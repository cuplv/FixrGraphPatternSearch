FROM ubuntu:16.04


################################################################################
# Install dependencies
################################################################################

# openssh-server, gcc, make, sudo, cmake, apt-transport-https
RUN apt-get update -qq -y \
    && apt-get install -y openssh-server gcc make sudo cmake apt-transport-https software-properties-common binutils g++ glpk-utils libglpk-dev python-cffi libssl-dev time binutils ant python python-pip python-sqlalchemy curl wget perl bzip2 unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN sudo pip install nose six protobuf requests

# Google protobuffer
RUN sudo apt-get update && apt-get install -y autoconf automake libtool
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
 && python scripts/mk_make.py \
 && cd build \
 && make \
 && sudo make install \
 && cd / \
 && rm -rf "$Z3_DIR"


RUN apt-get install -y git
RUN pip install flask

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

RUN mkdir /persist
RUN chown -R biggroum:admin /persist

EXPOSE 8081

RUN usermod -a -G sudo biggroum
RUN sed -s "s:%sudo:sudo:" -i /etc/sudoers
RUN echo "biggroum ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers


USER biggroum
WORKDIR /home/biggroum

RUN echo "Cloning repo..."

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
RUN protoc -I=./biggroum/FixrGraphExtractor/src/main/protobuf --python_out=./biggroum/python/fixrgraph/annotator/protobuf ./biggroum/FixrGraphExtractor/src/main/protobuf/proto_acdfg.proto \
    && protoc -I=./biggroum/FixrGraphExtractor/src/main/protobuf --python_out=./biggroum/python/fixrgraph/annotator/protobuf ./biggroum/FixrGraphExtractor/src/main/protobuf/proto_iso.proto \
    && protoc -I=./biggroum/FixrGraphIso/src/fixrgraphiso/protobuf:./biggroum/FixrGraphExtractor/src/main/protobuf --python_out=./biggroum/python/fixrgraph/annotator/protobuf ./biggroum/FixrGraphIso/src/fixrgraphiso/protobuf/proto_acdfg_bin.proto ./biggroum/FixrGraphIso/src/fixrgraphiso/protobuf/proto_unweighted_iso.proto ./biggroum/FixrGraphIso/src/fixrgraphiso/protobuf/proto_search.proto

# Include the project in the PYTHONPATH variable
ENV PYTHONPATH=/home/biggroum/biggroum/python:$PYTHONPATH
ENV PYTHONPATH=/home/biggroum/biggroum/FixrGraphPatternSearch:$PYTHONPATH

WORKDIR /home/biggroum/biggroum/FixrGraphPatternSearch

COPY wrapper_start.bash wrapper_start.bash

ENTRYPOINT ["/bin/bash", "wrapper_start.bash"]