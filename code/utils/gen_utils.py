import random

import numpy as np
import pandas as pd
import torch
from dataset.mutag_utils import GraphSampler, data_to_graph
from scipy.sparse import csr_matrix
import scipy.sparse as sp
from scipy.special import softmax
from torch_geometric.utils import from_scipy_sparse_matrix, k_hop_subgraph, to_scipy_sparse_matrix


def list_to_dict(preds):
    preds_dict = pd.DataFrame(preds).to_dict("list")
    for key in preds_dict.keys():
        preds_dict[key] = np.array(preds_dict[key])
    return preds_dict


def get_subgraph(node_idx, x, edge_index, num_hops, **kwargs):
    num_nodes, num_edges = x.size(0), edge_index.size(1)

    subset, edge_index, mapping, edge_mask = k_hop_subgraph(
        node_idx, num_hops, edge_index, relabel_nodes=True, num_nodes=num_nodes
    )

    x = x[subset]
    for key, item in kwargs.items():
        if torch.is_tensor(item) and item.size(0) == num_nodes:
            item = item[subset]
        elif torch.is_tensor(item) and item.size(0) == num_edges:
            item = item[edge_mask]
        kwargs[key] = item

    return x, edge_index, mapping, edge_mask, subset, kwargs


def from_edge_index_to_adj(edge_index, edge_weight, max_n):
    adj = to_scipy_sparse_matrix(edge_index, edge_attr=edge_weight).toarray()
    assert len(adj) <= max_n, "The adjacency matrix contains more nodes than the graph!"
    if len(adj) < max_n:
        adj = np.pad(adj, (0, max_n - len(adj)), mode="constant")
    return torch.FloatTensor(adj)


def from_adj_to_edge_index(adj):
    A = csr_matrix(adj)
    edges, edge_weight = from_scipy_sparse_matrix(A)
    return edges, edge_weight


def from_edge_index_to_sparse_adj(edge_index, edge_weight, max_n):
    adj = sp.coo_matrix((edge_weight, (edge_index[0, :], edge_index[1, :])), shape=(max_n, max_n), dtype=np.float32)
    return adj


def from_sparse_adj_to_edge_index(adj):
    adj = adj.tocoo().astype(np.float32)
    edge_index = torch.from_numpy(np.vstack((adj.row, adj.col)).astype(np.int64))
    edge_weight = torch.from_numpy(adj.data)
    return edge_index, edge_weight


def init_weights(edge_index):
    edge_weights = []
    for edges in edge_index:
        edges_w = torch.ones(edges.size(1))
        edge_weights.append(edges_w)
    return edge_weights


def get_test_nodes(data, model, args):
    if args.dataset.startswith("syn"):
        if eval(args.true_label_as_target):
            pred_labels = get_labels(model(data.x, data.edge_index).cpu().detach().numpy())
            list_node_idx = np.where(pred_labels == data.y.cpu().numpy())[0]
        else:
            list_node_idx = np.arange(data.x.size(0))
        list_node_idx_pattern = list_node_idx[list_node_idx > args.num_basis]
        # list_test_nodes = [x.item() for x in list_node_idx_pattern[: args.num_test]]
        list_test_nodes = [x.item() for x in np.random.choice(list_node_idx_pattern, size=args.num_test, replace=False)]
    else:
        if eval(args.true_label_as_target):
            pred_labels = get_labels(model(data.x, data.edge_index, edge_weight=data.edge_weight).cpu().detach().numpy())
            list_test_nodes = np.where(pred_labels == data.y.cpu().numpy())[0]
            list_test_nodes = [x.item() for x in np.random.choice(list_test_nodes, size=args.num_test, replace=False)]
        else:
            list_test_nodes = np.arange(data.x.size(0))
            list_test_nodes = [x.item() for x in np.random.choice(list_test_nodes, size=args.num_test, replace=False)]
    return list_test_nodes


def get_test_graphs(data, args):
    list_test_idx = np.random.randint(0, len(data), args.num_test)
    test_data = [data[index] for index in list_test_idx]
    return test_data


def gen_dataloader(graphs, args, max_nodes=0):
    dataset_sampler = GraphSampler(
        graphs,
        normalize=False,
        max_num_nodes=max_nodes,
        features=args.feature_type,
    )
    dataset_loader = torch.utils.data.DataLoader(
        dataset_sampler,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
    return dataset_loader


def get_true_labels_gc(dataset):
    labels = []
    for data in dataset:
        labels.append(int(data["label"]))
    return labels


def get_true_labels_gc_batch(dataset):
    labels = []
    for batch_idx, data in enumerate(dataset):
        labels.append(data["label"].long().numpy())
    labels = np.hstack(labels)
    return labels


def get_proba(ypred):
    yprob = softmax(ypred, axis=1)
    return yprob


def get_labels(ypred):
    ylabels = np.argmax(ypred, axis=1)
    return ylabels
