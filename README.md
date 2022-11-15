# 404checker
Auxiliary script thought to be used in Red Team exercises to check if an URL redirects to a masked 404 (such as 200 that redirects to a "Not found" page or similars). 
URLs must be passed sorted in order to improve performance.

## Usage
```
python3 404checker.py -h 
usage: 404checker.py [-h] -i INPUT_FILE -o OUTPUT_FILE [-v]

options:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input_file INPUT_FILE
                        Input file with urls on it (one per line)
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        Output file with good urls (one per line)
  -v, --verbose         Be verbose

```

## Results

The tool will output all the URLs that are not being redirected to a custom 404 page.