#!/bin/bash

export SEARCH_DATA_URL=https://drive.google.com/file/d/1LG2e_YMf6ms3ri7s-N34MhaIyfsFYwWD/view?usp=sharing
export SEARCH_ARCHIVE_NAME=solr_groum.tar.bz2

curl -L https://github.com/circulosmeos/gdown.pl/raw/master/gdown.pl -o gdown.pl \
  && perl ./gdown.pl $SEARCH_DATA_URL $SEARCH_ARCHIVE_NAME \
  && tar xjf $SEARCH_ARCHIVE_NAME \
  && rm -rf $SEARCH_ARCHIVE_NAME \
  && rm gdown.pl
