#!/bin/bash
for i in *.tgz; do
mkdir $i.dir;
cd $i.dir
tar xf ../$i
cd ..
done
