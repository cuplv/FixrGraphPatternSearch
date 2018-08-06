#!/bin/bash

# Note: we move the sitevisit_extraction folder OUTSIDE the docker
# context, otherwise docker copies all the data in the image!

fileid="1I43XNDa7ma5niPUsWVh1qEHhGy781sVH"
SEARCH_ARCHIVE_NAME="sitevisit_extraction.tar.gz2"
curl -c ./cookie -s -L "https://drive.google.com/uc?export=download&id=${fileid}" > /dev/null
curl -Lb ./cookie "https://drive.google.com/uc?export=download&confirm=`awk '/download/ {print $NF}' ./cookie`&id=${fileid}" -o ${SEARCH_ARCHIVE_NAME}

tar xjf $SEARCH_ARCHIVE_NAME \
  && rm -rf $SEARCH_ARCHIVE_NAME \
  && mv sitevisit_extraction ../ \
  && rm gdown.pl
