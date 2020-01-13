TODOs:
====
 - [x] revert button on challenge page
 - [ ] hints on challenge page (optionally)
 - [x] runc challenge solve infromation (bootstrap Modal component)
 - [x] runc challenge description popup (also Modal)
 - [x] review and fix esception handling in whole
 - [x] move everything besides routes from main.py
 - [x] implement abstract class for challenges
 - [x] create thread that will execute docker exec on runc challenge container
 - [ ] implement gVisor for running containers
 - [ ] implement limits for cpu, ram and disk usage
 - [ ] save internal container image to file to speedup building vulnerable container

Instalation
===========
 * install and setup nginx
   * `/etc/nginx/nginx.conf `
       ```
       user www-data;
       worker_processes auto;
       pid /run/nginx.pid;
       include /etc/nginx/modules-enabled/*.conf;
    
       events {
          	worker_connections 768;
       }
    
       http {
    	   sendfile on;
    	   tcp_nopush on;
    	   tcp_nodelay on;
    	   keepalive_timeout 65;
    	   types_hash_max_size 2048;
    	   include /etc/nginx/mime.types;
    	   default_type application/octet-stream;
    	   ssl_prefer_server_ciphers on;
    	   access_log /var/log/nginx/access.log;
    	   error_log /var/log/nginx/error.log;
    	   gzip on;
    	   include /etc/nginx/conf.d/*.conf;
    	   include /etc/nginx/sites-enabled/*.conf;
       }
       ```
    * `/etc/nginx/sites-enabled/container-escape.conf`
      ```
      server {
          listen 80;
        
          include /etc/nginx/sites-enabled/containers/*;
    
          location / {
              proxy_pass http://127.0.0.1:5000/;
              proxy_set_header X-Real-IP $remote_addr;
          }
      }
      ```
    * `mkdir /etc/nginx/sites-enabled/containers/`
 * install docker
