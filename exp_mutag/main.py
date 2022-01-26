import os
import re
import sys,os
sys.path.append(os.getcwd())

import torch
from torch_geometric.data import download_url


from gen_utils import check_dir
from dataset import extract_zip, extract_gz, process_mutag, collate_data


data_name = 'mutag'
data_save_dir = os.path.join('data', data_name)

check_dir(data_save_dir)
raw_data_dir = os.path.join(data_save_dir, 'raw_data')
# Save data_list
data_filename = os.path.join(data_save_dir, data_name) + '.pt'

#download MUTAG from url and put it in raw_dir
url = 'https://github.com/divelab/DIG_storage/raw/main/xgraph/datasets/MUTAG.zip'

path = download_url(url, raw_data_dir)
if url[-2:] == 'gz':
    extract_gz(path, raw_data_dir)
    os.unlink(path)
elif url[-3:] == 'zip':
    extract_zip(path, raw_data_dir)
    os.unlink(path)

data_list = process_mutag(raw_data_dir)
torch.save(collate_data(data_list), data_filename)