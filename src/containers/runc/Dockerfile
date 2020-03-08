FROM docker:dind

COPY runc-1.0.0-rc6-vulnerable /usr/local/bin/runc
#COPY ./vulnerable_container/ttyd_linux.x86_64 /opt
#COPY ./vulnerable_container/Dockerfile /opt
COPY ./runc_vuln.tar /opt

ENTRYPOINT ["dockerd-entrypoint.sh"]
