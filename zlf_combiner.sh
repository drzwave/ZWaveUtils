#!/bin/bash

# Script to combine multiple Z-Wave Zniffer files in a directory into a single file - combined_trace.zlf.
# A single larger Zniffer file is sometimes easier to debug a problem by gluing all the data into one file.
# This script has not been extensively tested and was reverse engineered so Use At Your Own Risk.

# Declare a combined file
COMBINED_FILE=combined_trace.zlf

# Delete it if it exists
rm -f $COMBINED_FILE

# Get a list of ZLF files to combine
ZLF_FILES=$(find . -iname "*.zlf" | sort -n)

# Create an empty file to combine ZLFs in
touch $COMBINED_FILE

# Boolean variable to add a header in the combined file
count=0

for f in $ZLF_FILES
do
    # If this is the first processed file
    if [ $count == 0 ] ; then
        # Add this file's header to the combined trace
        head -c2048 $f >> $COMBINED_FILE
        first=false
    fi

    # Add this file's non-header data to the combined trace
    tail -c+2049 $f >> $COMBINED_FILE

    # Increment the count
    let "count += 1"
done

# Print a useful message
echo Combined $count files into $COMBINED_FILE
