FROM ubuntu:16.04

################################################################################
# Install dependencies
################################################################################

# openssh-server, gcc, make, sudo, cmake, apt-transport-https
RUN apt-get update -qq -y \
    && apt-get install -y openssh-server gcc make sudo cmake \
    apt-transport-https software-properties-common binutils \
    g++ glpk-utils libglpk-dev python-cffi libssl-dev time \
    ant python python-pip python-sqlalchemy curl wget \
    unzip autoconf automake libtool \
    perl bzip2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install libgit2 library
RUN sudo mkdir app \
    && cd app \
    && curl -OL https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz \
    && ls \
    && tar xzf v0.27.0.tar.gz \
    && cd libgit2-0.27.0/ \
    && mkdir build && cd build \
    && cmake .. \
    && cmake --build . --target install \
    && sudo ldconfig \
    && rm -rf /app

RUN sudo pip install nose six pygit2 protobuf

# Oracle Java Jdk 8
RUN \
  echo oracle-java8-installer \
  shared/accepted-oracle-license-v1-1 select true | debconf-set-selections && \
  add-apt-repository -y ppa:webupd8team/java && \
  apt-get update && \
  apt-get install -y oracle-java8-installer && \
  rm -rf /var/lib/apt/lists/* && \
  rm -rf /var/cache/oracle-jdk7-installer
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle

# sbt
RUN echo "deb https://dl.bintray.com/sbt/debian /" | sudo tee -a /etc/apt/sources.list.d/sbt.list
RUN sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823
RUN sudo apt-get update
RUN sudo apt-get install -y sbt

# Google protobuffer
RUN curl -OL https://github.com/google/protobuf/releases/download/v3.5.0/protobuf-all-3.5.0.zip \
    && unzip protobuf-all-3.5.0.zip \
    && cd protobuf-3.5.0 \
    && ./autogen.sh \
    && ./configure \
    && make \
    && sudo make install \
    && sudo ldconfig \
    && cd .. \
    && rm -rf protobuf-3.5.0 protobuf-all-3.5.0.zip

# Microsoft z3
ENV Z3_VERSION "4.5.0"
# download, compile and install Z3
RUN Z3_DIR="$(mktemp -d)" \
 && cd "$Z3_DIR" \
 && wget -qO- https://github.com/Z3Prover/z3/archive/z3-${Z3_VERSION}.tar.gz | tar xz --strip-components=1 \
 && python scripts/mk_make.py --java \
 && cd build \
 && make \
 && sudo make install \
 && cd / \
 && rm -rf "$Z3_DIR"


################################################################################
# Set up user
# Run everything in the user space now
################################################################################
RUN mkdir /var/run/sshd
RUN chmod 0755 /var/run/sshd
RUN useradd -m biggroum
RUN groupadd admin
RUN usermod -a -G admin biggroum
RUN sudo chsh -s /bin/bash biggroum

# Filesystem
RUN mkdir /persist
RUN chown -R biggroum:admin /persist

RUN usermod -a -G sudo biggroum
RUN sed -s "s:%sudo:sudo:" -i /etc/sudoers
RUN echo "biggroum ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN sudo pip install requests

EXPOSE 8081
EXPOSE 5000


################################################################################
# Now in userspace
#
################################################################################

USER biggroum
WORKDIR /home/biggroum

RUN mkdir .ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

# Clone our repositories
RUN git clone https://github.com/cuplv/biggroum \
    && cd biggroum \
    && git submodule update --init --recursive

# Build the graph mining/frequent itemset mining tool
RUN cd biggroum/FixrGraphIso \
    && mkdir build \
    && cd build \
    && cmake ../ -DFIXR_GRAPH_EXTRACTOR_DIRECTORY=../../FixrGraphExtractor \
    && make \
    && cd ../../

# Build the protobuffer files
RUN protoc -I=./biggroum/FixrGraphExtractor/src/main/protobuf \
    --python_out=./biggroum/python/fixrgraph/annotator/protobuf \
    ./biggroum/FixrGraphExtractor/src/main/protobuf/proto_acdfg.proto \
    && protoc -I=./biggroum/FixrGraphExtractor/src/main/protobuf \
    --python_out=./biggroum/python/fixrgraph/annotator/protobuf \
    ./biggroum/FixrGraphExtractor/src/main/protobuf/proto_iso.proto

# Include the project in the PYTHONPATH variable
ENV PYTHONPATH=/home/biggroum/biggroum/python:$PYTHONPATH
ENV PYTHONPATH=/home/biggroum/biggroum/FixrGraphPatternSearch:$PYTHONPATH

RUN cd /home/biggroum/biggroum/FixrService-Backend && sbt stage

RUN cat /dev/zero | ssh-keygen -q -N "" -f ~/.ssh/id_rsa \
    && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys \
    && echo "StrictHostKeyChecking no" >> ~/.ssh/config

COPY wrapper_start.bash wrapper_start.bash

ENTRYPOINT ["/bin/bash", "wrapper_start.bash"]
