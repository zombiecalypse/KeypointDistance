KeypointDistance
================

This script can help you finding a good location for your appartment:

Say you don't live with your partner (they live in A), you got a job in B, and
your friends live in C and D. Now you don't want to spend all your life on the
road, so you want to minimize the commuting-distance to all places. This tool
takes two files, the options and the keypoints, and sorts the options by
feasibility (it prints the commuting score in hours).

The options file contains one address per line.

The keypoints file contains lines containing a double in the first column,
that signifies the relative importance of the point (higher is more important)
and the address of the point after a single space.
