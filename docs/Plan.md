# Confluence Fetcher - Development Plan

## Goal
Create a CLI tool that exports pages from Confluence to a local directory in specified formats (initially Markdown, with future extensibility to Word and PDF).

## Tooling
*   **Programming Language:** Python
*   **API Interaction:** `requests` library for making HTTP requests to the Confluence Cloud REST API.
*   **HTML Parsing:** `BeautifulSoup` (or similar) for parsing HTML content to extract relevant information and manipulate links.
*   **HTML to Markdown Conversion:** `pandoc` command-line tool.
*   **File System Operations:** Python's built-in `os` and `pathlib` modules for directory creation and file writing.

## CLI Arguments
*   `-a <accountname>`: Confluence account name (mandatory).
*   `-d <outputdir>`: Local output directory (mandatory).
*   `-s <spaces>`: Comma-separated list of space keys to fetch (optional).
*   `-f <outputformat>`: Output format (e.g., `markdown`, `word`, `pdf`).

## Milestone 1: Directory Structure Scaffolding

### Goal
Create a script that connects to Confluence, fetches all spaces, and creates a local directory for each space. This milestone focuses on setting up the basic API connection and file system operations, without handling page content.

### Core Logic
1.  **Authentication:**
    *   Retrieve the Confluence API token from the `CONFL_API_TOKEN` environment variable.
    *   Set up basic authentication for API requests.
2.  **Fetch Spaces:**
    *   Call `GET /wiki/api/v2/spaces` to retrieve a list of all available spaces.
    *   Implement pagination to handle multiple pages of results.
3.  **Create Local Directories:**
    *   For each space retrieved, sanitize its name to be a valid directory name.
    *   If the `-s` argument is provided, only create directories for the specified spaces.
    *   Create a corresponding directory in the specified `<outputdir>`.

## Milestone 1A: Fetch and List Pages

### Goal
Extend the script to iterate through each space, fetch its pages, and print the page titles. This verifies page-level API access and provides a foundation for content export.

### Core Logic
1.  **Fetch Pages for Each Space:**
    *   After creating the directory for a space, use its `id` to call `GET /wiki/api/v2/spaces/{id}/pages`.
    *   Implement pagination to handle spaces with many pages.
2.  **Print Page Titles:**
    *   For each page retrieved, print its title to the console. This confirms that the page fetching logic is working correctly.

## Milestone 2: Full Content Export

### Goal
Extend the script from Milestone 1 to a full-fledged solution that fetches pages and their attachments, converts content to Markdown, and saves everything in a structured local archive.

### Core Logic
1.  **Fetch Pages within Each Space:**
    *   For each space, call `GET /wiki/api/v2/spaces/{id}/pages` to get all pages.
    *   Implement pagination.
2.  **Local File System Management:**
    *   Adopt a hierarchical directory structure:
        ```
        <outputdir>/
        ├── <space_name_1>/
        │   ├── <sanitized_page_title_1>/
        │   │   ├── page.md
        │   │   └── attachments/
        │   │       └── <attachment_name_1>.<ext>
        │   └── <sanitized_page_title_2>/
        │       ├── page.md
        │       └── attachments/
        │           └── <attachment_name_3>.<ext>
        └── <space_name_2>/
            └── ...
        ```
3.  **Process Each Page:**
    *   For each page:
        *   Create the page-specific directory (e.g., `<outputdir>/<space_name>/<sanitized_page_title>/`).
        *   **Get Page Content:** Call `GET /wiki/api/v2/pages/{id}` with `expand=body.storage` to get the HTML content.
        *   **Get Page Attachments:**
            *   Call `GET /wiki/api/v2/pages/{id}/attachments`.
            *   Create the `attachments` subdirectory.
            *   Download each attachment using its `downloadLink` and save it locally.
4.  **Content Conversion and Saving:**
    *   **Attachment Link Rewriting:** Parse the page's HTML to update all attachment links to point to the local relative paths.
    *   **HTML to Markdown Conversion:** Use `pandoc` to convert the modified HTML to Markdown.
    *   **Save Markdown:** Save the final content to `page.md` within the page's directory.

## Future Enhancements (Beyond initial Markdown export)
*   Handle different `body-format` options if `export_view` is not sufficient.
*   More robust error handling and logging.
*   Configuration file for API settings.
