import os
from dotenv import load_dotenv
import pysharepoint as ps
from typing import Optional, Union

StrPath = Union[str, 'os.PathLike[str]']


def download_file(
        source_path: str,
        dest_dir: str,
        filename: str,
        sharepoint_base_url: str='',
        sharepoint_site: str='',
        dotenv_path: Optional[StrPath]=None
):
    # Check if ".env" file exists
    if not os.path.exists('.env'):
        _e = 'File ".env" does not exist. Create this file with your '
        _e += 'MS Office credencials. For more info, read README.md'
        raise FileNotFoundError(_e)

    if dotenv_path is None:
        load_dotenv()
    else:
        load_dotenv(dotenv_path)

    user_name = os.environ.get('EMAIL')
    password = os.environ.get('PASSWORD')
    if user_name is None:
        raise NameError('"EMAIL" not found in .env')
    if password is None:
        raise NameError('"password" not found in .env')

    site = ps.SPInterface(sharepoint_base_url, user_name, password)
    site.download_file_sharepoint(source_path, dest_dir, filename, sharepoint_site)


def upload_file(
        source_dir: str,
        dest_path: str,
        filename: str,
        sharepoint_base_url: str= '',
        sharepoint_site: str='',
        dotenv_path: Optional[StrPath]=None
):
    # Check if ".env" file exists
    if not os.path.exists('.env'):
        _e = 'File ".env" does not exist. Create this file with your '
        _e = 'MS Office credencials. For more info, read README.md'
        raise FileNotFoundError(_e)

    if dotenv_path is None:
        load_dotenv()
    else:
        load_dotenv(dotenv_path)

    user_name = os.environ.get('EMAIL')
    password = os.environ.get('PASSWORD')
    if user_name is None:
        raise NameError('"EMAIL" not found in .env')
    if password is None:
        raise NameError('"password" not found in .env')

    site = ps.SPInterface(sharepoint_base_url, user_name, password)
    site.upload_file_sharepoint(source_dir, dest_path, filename, sharepoint_site)


if  __name__ == '__main__':
    if os.path.exists(os.path.join(os.getcwd(), 'tmp')) is False:
        os.mkdir(os.path.join(os.getcwd(), 'tmp'))

    download_file(
            source_path='Shared Documents/General/Simulations_WIP',
            dest_dir=os.path.join(os.getcwd(), 'tmp'),
            filename='test_download_upload.txt'
    )

    f = open(os.path.join(os.getcwd(), 'tmp', 'test_download_upload.txt'), 'w')
    f.write('apple bitten')
    f.close()

    upload_file(
            source_dir=os.path.join(os.getcwd(), 'tmp'),
            dest_path='Shared Documents/General/Simulations_WIP',
            filename='test_download_upload.txt'
    )
