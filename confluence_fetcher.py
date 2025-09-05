from typing import List
import os
import argparse
import re
import subprocess
from bs4 import BeautifulSoup, Tag
from confluence_client import ConfluenceClient, ConfluenceAPIError


def sanitize_directory_name(name: str) -> str:
    """Sanitizes a string to be a valid directory name."""

    # Remove invalid characters
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace spaces with underscores
    sanitized_name = sanitized_name.replace(' ', '_')
    return sanitized_name


def html_to_markdown(html_content: str) -> str | None:
    """Converts HTML to Markdown using pandoc."""

    try:
        process = subprocess.run(
            ['pandoc', '-f', 'html', '-t', 'markdown'],
            input=html_content,
            text=True,
            capture_output=True,
            check=True
        )
        return process.stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error during pandoc conversion: {e}")
        if isinstance(e, FileNotFoundError):
            print("Pandoc is not installed or not in the system's PATH.")
        return None


def process_spaces(spaces: List[dict], args: argparse.Namespace, client: ConfluenceClient) -> None:
    for space in spaces:
        space_name = space.get('name', 'Untitled_Space')
        space_key = space.get('key', 'NO_KEY')
        sanitized_name = sanitize_directory_name(space_name)
        space_dir = os.path.join(args.outputdir, sanitized_name)
        os.makedirs(space_dir, exist_ok=True)
        print(f"  - Created directory for space: '{space_name}' (Key: {space_key}) -> {sanitized_name}")
        print(f"\nProcessing Space: '{space_name}' (Key: {space_key})")

        space_id = space.get('id')
        if not space_id:
            print(f"  Warning: No ID found for space '{space_name}' (Key: {space_key})")
            continue

        print(f"  Fetching pages for space '{space_name}'...")

        try:
            pages = client.get_pages_for_space(space_id)
        except ConfluenceAPIError as e:
            print(f"  Error processing space: {e}")
            continue
    
        print(f"  Found {len(pages)} pages.")
        for page in pages:
            page_title = page.get('title', 'Untitled Page')
            sanitized_page_title = sanitize_directory_name(page_title)
            page_dir = os.path.join(space_dir, sanitized_page_title)
            os.makedirs(page_dir, exist_ok=True)
            print(f"\n  Processing page: '{page_title}'")
            export_page_content(page, page_dir, client)

    print("\nDone.")


def parse_and_validate_args() -> tuple[argparse.Namespace, ConfluenceClient]:
    parser = argparse.ArgumentParser(description="Fetch Confluence spaces and create directories.")
    parser.add_argument('-a', '--accountname', required=True, help='Confluence account name.')
    parser.add_argument('-d', '--outputdir', required=True, help='Local output directory.')
    parser.add_argument('-s', '--spaces', help='Comma-separated list of space keys to fetch.')
    args = parser.parse_args()

    try:
        client = ConfluenceClient(
            account_name=args.accountname,
            user_email=os.getenv('CONFL_USER_EMAIL', ''),
            api_token=os.getenv('CONFL_API_TOKEN', '')
        )
        return args, client
    except ValueError as e:
        print(f'Error: {e}')
        exit(1)


def handle_attachments(page_dir: str, page: dict, client: ConfluenceClient) -> None:
    attachments_dir = os.path.join(page_dir, 'attachments')
    attachments = client.get_page_attachments(page['id'])
    if attachments:
        os.makedirs(attachments_dir, exist_ok=True)
        print(f"    Found {len(attachments)} attachments.")
        
        for attachment in attachments:
            file_name = attachment.get('title')
            download_link = attachment.get('_links', {}).get('download')
            if file_name and download_link:
                try:
                    content = client.download_attachment(download_link)
                    file_path = os.path.join(attachments_dir, file_name)
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"      Downloaded: {file_name}")
                except ConfluenceAPIError as e:
                    print(f"      Error downloading {file_name}: {e}")


# Rewrite links in HTML
def rewrite_links(html_content: str) -> str:
    """Rewrites attachment links in HTML content to point to local files."""

    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup.find_all(['img', 'a']):
        if not isinstance(tag, Tag):
            continue
        attr = 'src' if tag.name == 'img' else 'href'
        link = tag.get(attr)
        if isinstance(link, str) and '/download/attachments/' in link:
            file_name = os.path.basename(link.split('?')[0])
            tag[attr] = f"attachments/{file_name}"
    return str(soup)


def export_page_content(page: dict, page_dir: str, client: ConfluenceClient) -> None:
    """Process a single page's content and attachments."""

    try:
        page_content = client.get_page_content(page['id'])
    except ConfluenceAPIError as e:
        print(f"    Error fetching page content: {e}")
        return

    html_content = page_content.get('body', {}).get('storage', {}).get('value')
    if not html_content:
        print(f"    No content found for page: {page.get('title', 'Untitled Page')}")
        return

    try:
        handle_attachments(page_dir, page, client)
    except ConfluenceAPIError as e:
        print(f"    Error fetching attachments: {e}")

    # Process HTML content
    modified_html = rewrite_links(html_content)

    # Convert to Markdown
    markdown_content = html_to_markdown(modified_html)
    if not markdown_content:
        return

    md_file_path = os.path.join(page_dir, 'page.md')
    with open(md_file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"    Saved page content to: {md_file_path}")


def prepare_output_directory(spaces: List[dict] | None, conf_spaces: str, output_dir: str) -> List[dict]:
    if not spaces:
        print('No spaces found or error fetching spaces.')
        exit(1)

    if spaces:
        selected_space_keys = [key.strip() for key in conf_spaces.split(',')]
        print(selected_space_keys)
        spaces = [s for s in spaces if s.get('key') in selected_space_keys]
        print(f"Filtering for spaces: {', '.join(selected_space_keys)}")

    print(f"Found {len(spaces)} spaces. Creating directories in {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    return spaces


def main():
    """Main function to execute the script."""

    args, client = parse_and_validate_args()

    print(f"Fetching spaces from {args.accountname}...")
    try:
        spaces = client.get_spaces()
    except ConfluenceAPIError as e:
        print(f"Error getting spaces: {e}")
        exit(1)

    spaces = prepare_output_directory(spaces, args.spaces, args.outputdir)
    process_spaces(spaces, args, client)


if __name__ == '__main__':
    main()
