import subprocess
import threading
import docker
import time
import os

from challenges.challenge import Challenge
from main import app
import utils


class Mount(Challenge):
    def __init__(self, client, solved_challenges):
        self.client = client
        self.solved_challenges = solved_challenges
        self.lock = threading.Lock()
        self.is_removed = False

    @property
    def title(self):
        return "Mounting host drive"

    @property
    def subtitle(self):
        return "Wrong permissions"

    @property
    def description(self):
        return """Running host with --privileged flag gives capabilities
        to mount host drive into docker. This way you can manage host files."""

    def run_instance(self, user_id):
        self.lock.acquire()
        port = utils.get_free_port()

        if port == -1:
            raise Exception("failed to run instance, couldn't find available port")

        try:
            container = self.client.containers.run(
                ports={f"{port}/tcp": f"{port}/tcp"},
                privileged=True,
                remove=True,
                name=user_id,
                detach=True,
                image="mount_vuln_host",
                mem_limit="250m",
                memswap_limit="250m",  # when swap limit is the same as mem, then container doesn't have access to swap
                cpu_shares=512,  # cpu cycles limit
                # storage_opt={'size': '512m'},  # https://stackoverflow.com/questions/33013904/how-to-limit-docker-filesystem-space-available-to-containers
            )
            self.run_vulnerable_container(container, port)
            self.create_nginx_config(user_id, port)
            app.logger.info(f"challenge container created for {user_id}")
        except (docker.errors.BuildError, docker.errors.APIError) as e:
            app.logger.error(f"container build failed for {user_id}: {e}")
        except Exception as e:
            app.logger.error(
                f"unknown error while building container for {user_id}: {e}"
            )
        self.lock.release()

    def remove_instance(self, user_id):
        self.is_removed = True
        try:
            os.remove(f"/etc/nginx/sites-enabled/containers/{user_id}.conf")
            app.logger.info(f"removed nginx config for {user_id}")
        except OSError as e:
            app.logger.error(f"failed to remove instance: {e}")

        try:
            container = self.client.containers.get(user_id)
            container.stop()
            # This try-except block and while loop below is required, because the
            # stop function from Docker SDK sometimes returns even when container
            # still exist, what caused some conflicts while reverting container.
            # If container doesn't exists get function will throw 404 not found
            # error, which will be caught, by except block. Otherwise thread will
            # sleep for 1 second and try to get container again
            try:
                while self.client.containers.get(user_id):
                    time.sleep(1)
            except Exception:
                pass

            if container.name in self.solved_challenges:
                self.solved_challenges.remove(container.name)
            app.logger.info(f"stopped container for {user_id}")
        except docker.errors.APIError as e:
            app.logger.error(f"failed to remove instance: {e}")
            app.logger.warning(f"container {user_id} might need manual removal")

    def build_challenge(self):
        # first element in the returned tuple from build function is Image object
        image = self.client.images.build(
            tag="mount_vuln", path="./containers/mount/vulnerable_container/"
        )[0].save()
        with open("./containers/mount/mount_vuln.tar", "wb") as f:
            for chunk in image:
                f.write(chunk)
        self.client.images.build(tag="mount_vuln_host", path="./containers/mount/")
        app.logger.info("mount challenge image successfully builded")

    def create_nginx_config(self, user_id, port):
        config = "location /challenges/mount/%s/ {\n" % user_id
        config += "    proxy_pass http://127.0.0.1:%s/;\n" % port
        config += "    proxy_http_version 1.1;\n"
        config += "    proxy_set_header X-Real-IP $remote_addr;\n"
        config += "    proxy_set_header Upgrade $http_upgrade;\n"
        config += '    proxy_set_header Connection "Upgrade";\n'
        config += "}\n"

        config_path = f"/etc/nginx/sites-enabled/containers/{user_id}.conf"
        try:
            with open(config_path, "w+") as f:
                f.write(config)
        except OSError:
            raise Exception("nginx config file open failed")

        res = subprocess.call(["/usr/sbin/nginx", "-s", "reload"])
        if res != 0:
            raise Exception("nginx reload failed (non zero exit code)")
        app.logger.info(f"nginx config created and reloaded for {user_id}")

    def run_vulnerable_container(self, container, port):
        docker_soc_check = (
            """sh -c 'test -e /var/run/docker.sock && echo -n "1" || echo -n "0"' """
        )

        while container.exec_run(docker_soc_check)[1].decode("utf-8") != "1":
            time.sleep(0.5)

        load_result = container.exec_run("docker load --input /opt/mount_vuln.tar")
        if load_result[0] != 0:  # check if command exit code is 0
            raise Exception(
                f'internal container build failed:\n{load_result[1].decode("utf-8")}'
            )

        container_id = load_result[1].decode("utf-8").strip().split(":")[2]
        tag_result = container.exec_run(f"docker tag {container_id} vuln")
        if tag_result[0] != 0:
            raise Exception(
                f'internal container tag failed:\n{tag_result[1].decode("utf-8")}'
            )

        # create a virtual disk
        run_result = container.exec_run(
            f"/root/create_disk.sh"
        )
        if run_result[0] != 0:  # check if command exit code is 0
            raise Exception(
                f'creation of virtual disk failed:\n{run_result[1].decode("utf-8")}'
            )

        # check which loop was used for mounting
        time.sleep(1)
        run_result = container.exec_run("cat /root/loop.txt", stdout=True, stderr=True)
        loop = run_result[1].decode("utf-8").replace('\n', '')
        if loop.strip() == '':
            app.logger.warning('Could not create loop device. Revert container!')
        # run docker in docker with mounts
        run_result = container.exec_run(
            f"docker run --device={loop}:/dev/s3cur3 --cap-add='SYS_ADMIN' -p {port}:8081 -d --restart unless-stopped vuln"
        )
        if run_result[0] != 0:  # check if command exit code is 0
            raise Exception(
                f'internal container run failed:\n{run_result[1].decode("utf-8")}'
            )
        # start win_check thread
        threading.Thread(target=self.win_check).start()

        app.logger.info(f"internal container created for {container.name}")

    def win_check(self):
        while True:
            time.sleep(1)
            for container in self.client.containers.list():
                try:
                    if self.is_removed:
                        break
                    if container.name.split('-')[0] == 'mount' and container.status == 'running':
                        result = container.exec_run('find /mnt/flag -name VICTORY', stdout=True, stderr=True)
                        checksum = result[1].decode('utf-8').strip()
                        if container.name not in self.solved_challenges:
                            if 'VICTORY' in ''.join(checksum) and result[0] == 0 and not self.is_removed:
                                app.logger.info(f'we got a win: {container.name}')
                                self.solved_challenges.append(container.name)
                except (docker.errors.NotFound, docker.errors.APIError):
                    continue
                except Exception as e:
                    app.logger.error(f'win check failed on {container.name} with error:\n{e}')
