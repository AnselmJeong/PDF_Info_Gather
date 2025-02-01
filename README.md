## Overview

This application is designed to process PDF files, extract informative snippets from them, and save them into a database. It can also aggregate the snippets into clusters centered around several themes.

## gather_snippets.py

The `gather_snippets.py` script is responsible for processing all PDF files located in a specified directory and gather informative snippets from them.

```
uv run gather_snippets.py -d <directory> -n <database_name> -p <provider>
```
- directory: the directory containing the PDF files to process. (default: ./documents)
- database_name: the name of the database to use for storing the snippets. (default: Clozapine_OCS)
- provider: the provider to use for querying the AI model. One of [qwen, deepseek, openai, groq] (default: qwen)


## gui.py

The `gui.py` script helps to overview the aggregated themes and associated snippets.
In order to use this GUI, snippets must have been gathered and stored first.

```
uv run gui.py
```

## Conclusion

This application streamlines the process of extracting and managing information from PDF files, leveraging AI capabilities to enhance the quality of the output. Users can easily configure and run the application to suit their needs.

# End Generation Here
