#!/bin/bash

export SEARCH_DATA_URL=https://drive.google.com/file/d/1I43XNDa7ma5niPUsWVh1qEHhGy781sVH
export SEARCH_ARCHIVE_NAME=sitevisit_extraction.tar.gz2

curl -L https://github.com/circulosmeos/gdown.pl/raw/master/gdown.pl -o gdown.pl \
  && perl ./gdown.pl $SEARCH_DATA_URL $SEARCH_ARCHIVE_NAME \
  && tar xjf $SEARCH_ARCHIVE_NAME \
  && rm -rf $SEARCH_ARCHIVE_NAME \
  && rm gdown.pl
