import os
import requests
import argparse
import re
import subprocess
from bs4 import BeautifulSoup, Tag

def get_pages_for_space(account_name, user_email, api_token, space_id):
    """Fetches all pages for a given space from the Confluence API."""

    base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
    url = f"{base_url}/spaces/{space_id}/pages"
    auth = (user_email, api_token)
    headers = {
        "Accept": "application/json"
    }
    pages = []
    while url:
        try:
            response = requests.get(url, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()
            pages.extend(data.get('results', []))
            next_path = data.get('_links', {}).get('next')
            if next_path:
                url = f"https://{account_name}.atlassian.net{next_path}"
            else:
                url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching pages for space {space_id}: {e}")
            return None
    return pages

def sanitize_directory_name(name):
    """Sanitizes a string to be a valid directory name."""

    # Remove invalid characters
    sanitized_name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace spaces with underscores
    sanitized_name = sanitized_name.replace(' ', '_')
    return sanitized_name

def get_spaces(account_name, user_email, api_token):
    """Fetches all spaces from the Confluence API."""

    base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
    url = f"{base_url}/spaces"
    auth = (user_email, api_token)
    headers = {
        "Accept": "application/json"
    }

    spaces = []
    while url:
        try:
            response = requests.get(url, headers=headers, auth=auth)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            spaces.extend(data.get('results', []))
            next_path = data.get('_links', {}).get('next')
            if next_path:
                url = f"https://{account_name}.atlassian.net{next_path}"
            else:
                url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching spaces: {e}")
            return None
    return spaces

def get_page_content(page_id, account_name, user_email, api_token):
    """Gets the HTML content of a single page."""

    base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
    url = f"{base_url}/pages/{page_id}"
    params = {
        "body-format": "storage",
        "status": "current"
    }
    auth = (user_email, api_token)
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, auth=auth, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('body', {}).get('storage', {}).get('value')
    except requests.exceptions.RequestException as e:
        print(f"Error fetching content for page {page_id}: {e}")
        return None

def get_page_attachments(page_id, account_name, user_email, api_token):
    """Fetches all attachments for a given page."""

    base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
    url = f"{base_url}/pages/{page_id}/attachments"
    auth = (user_email, api_token)
    headers = {
        "Accept": "application/json"
    }

    attachments = []
    while url:
        try:
            response = requests.get(url, headers=headers, auth=auth)
            response.raise_for_status()
            data = response.json()
            attachments.extend(data.get('results', []))
            next_path = data.get('_links', {}).get('next')
            if next_path:
                url = f"https://{account_name}.atlassian.net{next_path}"
            else:
                url = None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching attachments for page {page_id}: {e}")
            return None
    return attachments

def download_attachment(download_url, file_path, auth):
    """Downloads a single attachment."""

    try:
        response = requests.get(download_url, auth=auth, stream=True)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        print(f"    Error downloading attachment: {e}")
        return False

def html_to_markdown(html_content):
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

def rewrite_links(html_content):
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

def export_page_content(page, page_dir, account_name, user_email, api_token):
    """Process a single page's content and attachments."""

    html_content = get_page_content(page['id'], account_name, user_email, api_token)
    if not html_content:
        print(f"    No content found for page: {page.get('title', 'Untitled Page')}")
        return

    # Handle attachments first
    attachments_dir = os.path.join(page_dir, 'attachments')
    attachments = get_page_attachments(page['id'], account_name, user_email, api_token)
    if attachments:
        os.makedirs(attachments_dir, exist_ok=True)
        print(f"    Found {len(attachments)} attachments.")
        auth = (user_email, api_token)
        base_url = f"https://{account_name}.atlassian.net"
        
        for attachment in attachments:
            file_name = attachment.get('title')
            download_link = attachment.get('_links', {}).get('download')
            if file_name and download_link:
                download_url = f"{base_url}{download_link}"
                file_path = os.path.join(attachments_dir, file_name)
                if download_attachment(download_url, file_path, auth):
                    print(f"      Downloaded: {file_name}")

    # Process HTML content
    modified_html = rewrite_links(html_content)
    markdown_content = html_to_markdown(modified_html)
    if markdown_content:
        md_file_path = os.path.join(page_dir, 'page.md')
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"    Saved page content to: {md_file_path}")

def main():
    """Main function to execute the script."""
    parser = argparse.ArgumentParser(description="Fetch Confluence spaces and create directories.")
    parser.add_argument("-a", "--accountname", required=True, help="Confluence account name.")
    parser.add_argument("-d", "--outputdir", required=True, help="Local output directory.")
    parser.add_argument("-s", "--spaces", help="Comma-separated list of space keys to fetch.")
    args = parser.parse_args()

    user_email = os.getenv("CONFL_USER_EMAIL")
    api_token = os.getenv("CONFL_API_TOKEN")
    if not api_token or not user_email:
        print("Error: CONFL_USER_EMAIL and CONFL_API_TOKEN environment variables must be set.")
        return

    print(f"Fetching spaces from {args.accountname}...")
    spaces = get_spaces(args.accountname, user_email, api_token)

    if spaces:
        if args.spaces:
            selected_space_keys = [key.strip() for key in args.spaces.split(',')]
            spaces = [s for s in spaces if s.get('key') in selected_space_keys]
            print(f"Filtering for spaces: {', '.join(selected_space_keys)}")

        print(f"Found {len(spaces)} spaces. Creating directories in {args.outputdir}...")
        os.makedirs(args.outputdir, exist_ok=True)

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
            pages = get_pages_for_space(args.accountname, user_email, api_token, space_id)
            if not pages:
                print("  No pages found or error fetching pages.")
                continue

            print(f"  Found {len(pages)} pages.")
            for page in pages:
                page_title = page.get('title', 'Untitled Page')
                sanitized_page_title = sanitize_directory_name(page_title)
                page_dir = os.path.join(space_dir, sanitized_page_title)
                os.makedirs(page_dir, exist_ok=True)
                print(f"\n  Processing page: '{page_title}'")
                export_page_content(page, page_dir, args.accountname, user_email, api_token)

        print("\nDone.")

if __name__ == "__main__":
    main()
