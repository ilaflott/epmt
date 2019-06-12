#!/bin/sh
rm -rf /tmp/epmt/615503
mkdir /tmp/epmt/615503
tar -C /tmp/epmt/615503 -xzf sample/uncollated/postprocruns/ESM4_historical_D151_atmos_18540101.papiex.615503.tgz
epmt -v -j 615503 stage
epmt -v submit ./615503.tgz
