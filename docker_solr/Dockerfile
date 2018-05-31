FROM ubuntu:16.04


RUN apt-get update
RUN apt-get install -y curl wget perl tar bzip2

# Data
ENV SOLR_CORE_URL https://drive.google.com/file/d/1o-aju6L_th3g0NrNqhA0ulTpSqJWyBWY
ENV SOLR_CORE_ARCHIVE solr_groum.tar.bz2
ENV SOLR_CORE_FOLDER_NAME solr_groum
ENV SOLR_CORE_PATH /opt/solr/$SOLR_CORE_FOLDER_NAME

# Install Solr
ENV SOLR_VERSION 5.3.1
ENV SOLR solr-$SOLR_VERSION

RUN curl --retry 3 http://archive.apache.org/dist/lucene/solr/$SOLR_VERSION/$SOLR.tgz | tar -C /opt --extract --gzip
RUN mv /opt/$SOLR /opt/solr
RUN useradd --home-dir /opt/solr --comment "Solr Server" solr

# RUN curl -L https://github.com/circulosmeos/gdown.pl/raw/master/gdown.pl -o gdown.pl
# RUN cd /opt/solr \
#     && perl /gdown.pl $SOLR_CORE_URL $SOLR_CORE_ARCHIVE \
#     && tar xjf $SOLR_CORE_ARCHIVE \
#     && rm -rf $SOLR_CORE_ARCHIVE
# RUN rm gdown.pl

RUN chown -R solr:solr /opt/solr
RUN mkdir /persist
RUN chown -R solr:solr /persist 
RUN apt-get update
RUN apt-get install -y unzip openjdk-8-jdk lsof

USER solr

EXPOSE 8983
WORKDIR /opt/solr

# opt/solr/solr_groum/solr
CMD ["bin/solr", "start", "-f", "-d", "server/", "-s", "/persistent/solr"]