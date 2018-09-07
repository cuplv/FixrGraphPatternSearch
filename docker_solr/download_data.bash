#!/bin/bash

# Note: we move the sitevisit_extraction folder OUTSIDE the docker
# context, otherwise docker copies all the data in the image!

fileid="1LG2e_YMf6ms3ri7s-N34MhaIyfsFYwWD"
SEARCH_ARCHIVE_NAME="solr_groum.tar.bz2"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${SEARCH_ARCHIVE_NAME}
tar xjf $SEARCH_ARCHIVE_NAME \
  && mv solr_groum ../ \
  && rm -rf $SEARCH_ARCHIVE_NAME \
  && rm gdown.pl
