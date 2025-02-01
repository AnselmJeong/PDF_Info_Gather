import urllib.parse
from pathlib import Path

BASE_URL = "http://anselmjeong.synology.me:8091/share/eYiYpS1n/"


def walk_directory_and_get_pdfs(directory):
    """
    Recursively get all PDF files from a directory and its subdirectories.
    Returns a list of relative paths to PDF files.
    """
    # Convert directory to Path object if it's a string
    directory = Path(directory)

    # Use glob pattern matching to find all PDFs recursively
    pdf_files = [path.relative_to(directory) for path in directory.rglob("*.pdf")]

    return pdf_files


def convert_filename_to_link(filename):
    # Base URL of the server

    # URL encode the filename
    encoded_filename = urllib.parse.quote(filename)

    # Combine base URL with encoded filename
    full_url = BASE_URL + encoded_filename

    return full_url


def get_links_of_pdf_in_directory(directory):
    """
    Find all PDFs in directory and convert their paths to links
    """
    pdf_files = walk_directory_and_get_pdfs(directory)

    for pdf_path in pdf_files:
        # Convert Path object to string for display and link conversion
        path_str = str(pdf_path)
        print(f"\nFile: {path_str}")
        link = convert_filename_to_link(path_str)
        print(f"Link: {link}")


# Example usage
if __name__ == "__main__":
    directory_path = Path("./documents")  # Current directory, change as needed
    get_links_of_pdf_in_directory(directory_path)
