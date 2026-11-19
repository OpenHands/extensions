#!/bin/sh
# Reproduces Debian's packaged Maven failing to load a Java 17+ plugin, and upstream Maven succeeding.
# Run from this directory: ./run.sh
set -u
IMAGE="${IMAGE:-ghcr.io/openhands/agent-canvas:latest}"
docker run --rm -u root -e DEBIAN_FRONTEND=noninteractive -v "$PWD":/repro -w /repro --entrypoint sh "$IMAGE" -c '
  set -u
  apt-get update -qq >/dev/null && apt-get install -y -qq --no-install-recommends openjdk-21-jdk-headless maven >/dev/null
  . /etc/os-release; echo "== $PRETTY_NAME"
  echo "== Debian maven package:"; mvn -v | head -1
  ls /usr/share/maven/lib | grep -i sisu
  mvn -B -q package 2>&1 | grep -m1 -E "NullInjected|BUILD" || echo "Debian maven: BUILD OK"
  echo "== Upstream Apache Maven 3.9.9:"
  curl -fsSL -o /tmp/m.tgz https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz
  echo "a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b  /tmp/m.tgz" | sha512sum -c - >/dev/null
  tar xzf /tmp/m.tgz -C /opt
  ls /opt/apache-maven-3.9.9/lib | grep -i "sisu.*jar"
  rm -rf target
  /opt/apache-maven-3.9.9/bin/mvn -B -q package && ls target/*.jar && echo "Upstream maven: BUILD OK"
'
