# Confluence Fetcher

This tool is a command-line interface (CLI) utility designed to fetch pages from a Confluence account and export them to a local directory. It converts page content to Markdown, downloads all associated attachments, and organizes the output in a clean, hierarchical structure.

## Features

* **Space-Specific Export:** Fetches all spaces or a specified subset using space keys.
* **Content Conversion:** Converts Confluence pages from HTML to Markdown using `pandoc`.
* **Attachment Handling:** Downloads all attachments for each page and places them in a dedicated `attachments` subdirectory.
* **Link Rewriting:** Automatically rewrites links to attachments within the Markdown content to point to the locally downloaded files.
* **Hierarchical Structure:** Organizes the exported content into a logical directory structure: `output_directory/<space_name>/<page_title>/`.

## Requirements

* Python 3.9+
* [Pandoc](https://pandoc.org/installing.html) must be installed and available in the system's PATH.
* Python libraries: `requests`, `beautifulsoup4`.

## Setup

1. **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd confluence-fetcher
    ```

2. **Install Python dependencies:**

    It is recommended to use a virtual environment.

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install requests beautifulsoup4
    ```

3. **Set Environment Variables:**

    The tool requires your Confluence email and an API token for authentication.

    ```bash
    export CONFL_USER_EMAIL="your_email@example.com"
    export CONFL_API_TOKEN="your_confluence_api_token"
    ```

    > **Note:** You can generate a Confluence API token by following the instructions [here](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).

## Usage

The script is executed from the command line with the following arguments:

* `-a`, `--accountname`: **(Required)** Your Confluence account name (the subdomain part of your Confluence URL, e.g., `your-company` from `your-company.atlassian.net`).
* `-d`, `--outputdir`: **(Required)** The local directory where the exported files will be saved.
* `-s`, `--spaces`: **(Optional)** A comma-separated list of space keys to fetch. If omitted, the tool will attempt to fetch all available spaces.

### Example

To export the "CREAT" and "DOCS" spaces from the "my-company" Confluence account into a local directory named `confluence_export`:

```bash
python confluence_fetcher.py \
    -a my-company \
    -d ./confluence_export \
    -s CREAT,DOCS
```

## Output Structure

The tool will generate a directory structure similar to the following:

```
<outputdir>/
├── <Space_Name_1>/
│   ├── <Page_Title_1>/
│   │   ├── page.md
│   │   └── attachments/
│   │       └── attachment1.png
│   └── <Page_Title_2>/
│       ├── page.md
│       └── attachments/
│           └── document.pdf
└── <Space_Name_2>/
    └── ...
```
