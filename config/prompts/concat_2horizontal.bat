ffmpeg -i %1 -i %2 -filter_complex "[0:v][1:v]hstack=inputs=2[v]" -map "[v]" 2horizontal.mp4