#!/bin/sh
cd "$(dirname "$0")"
printf "// generated from src/invoice.ts\n" > src/gen/types.gen.ts
