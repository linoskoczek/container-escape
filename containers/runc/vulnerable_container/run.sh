#!/bin/bash -x

docker build -t vuln .
docker run -p 8081:8081 -d --restart unless-stopped vuln
