#!/bin/bash

rm -f ncbitaxon_viruses.owl ncbitaxon_viruses.owl.gz ncbitaxon.owl

wget http://purl.obolibrary.org/obo/ncbitaxon.owl

robot extract --input ncbitaxon.owl --method TOP -t 'http://purl.obolibrary.org/obo/NCBITaxon_10239' --output ncbitaxon_viruses.owl
gzip ncbitaxon_viruses.owl

rm -f ncbitaxon.owl

