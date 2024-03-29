import numpy as np
import torch
from dataset.mutag_utils import prepare_data
from sklearn import metrics
from torch.autograd import Variable
from torch_geometric.loader import ClusterData, ClusterLoader, NeighborLoader
from tqdm import tqdm
from utils.gen_utils import from_adj_to_edge_index, get_labels
from utils.graph_utils import get_edge_index_batch


def gnn_accuracy(output, labels):
    preds = output.max(1)[1].type_as(labels)
    correct = preds.eq(labels).double()
    correct = correct.sum()
    return correct / len(labels)


def evaluate_nc_batch(model, data_loader, args, device):
    model.eval()
    total_loss = 0
    total_examples = 0
    for batch_idx in range(min(len(data_loader), args.batch_size)):
        batch = next(iter(data_loader))
        batch = batch.to(device)
        out = model(batch.x, batch.edge_index)
        loss = model.loss(out, batch.y)
        batch_size = batch.batch_size
        total_loss += float(loss) * batch_size
        total_examples += batch_size
    return total_loss / total_examples


def gnn_preds_nc_batch(model, data_loader, device):
    model.eval()
    pred_labels = []
    ypreds = []
    for batch in tqdm(data_loader):
        batch = batch.to(device)
        out = model(batch.x, batch.edge_index)
        _, indices = torch.max(out, 1)
        pred_labels.append(indices.cpu().data.numpy())
        ypreds.append(out.cpu().data.numpy())
    ypreds = np.concatenate(ypreds)
    return ypreds


def gnn_scores_nc(model, data, args, device):
    model.eval()

    if data.num_nodes > args.sample_size:
        cluster_data = ClusterData(data, num_parts=data.x.size(0) // args.sample_size, recursive=False)
        data_loader = ClusterLoader(cluster_data, batch_size=1, shuffle=True)  # , num_workers=args.num_workers)
        data = next(iter(data_loader))

    ypred = model(data.x, data.edge_index, edge_weight=data.edge_weight).cpu().detach().numpy()
    ylabels = get_labels(ypred)
    data.y = data.y.cpu()

    data.train_mask = data.train_mask.cpu()
    data.test_mask = data.test_mask.cpu()
    print("lenght of test mask", len(data.test_mask[data.test_mask == True]))

    result_train = {
        "prec": metrics.precision_score(data.y[data.train_mask], ylabels[data.train_mask], average="macro"),
        "recall": metrics.recall_score(data.y[data.train_mask], ylabels[data.train_mask], average="macro"),
        "f1-score": metrics.f1_score(data.y[data.train_mask], ylabels[data.train_mask], average="macro"),
        "acc": metrics.accuracy_score(data.y[data.train_mask], ylabels[data.train_mask]),
    }

    result_test = {
        "prec": metrics.precision_score(data.y[data.test_mask], ylabels[data.test_mask], average="macro"),
        "recall": metrics.recall_score(data.y[data.test_mask], ylabels[data.test_mask], average="macro"),
        "f1-score": metrics.f1_score(data.y[data.test_mask], ylabels[data.test_mask], average="macro"),
        "acc": metrics.accuracy_score(data.y[data.test_mask], ylabels[data.test_mask]),
    }
    return result_train, result_test


def gnn_scores_gc(model, dataset, args, device):
    train_dataset, val_dataset, test_dataset, max_num_nodes, feat_dim, assign_feat_dim = prepare_data(dataset, args)
    model.eval()
    result_train = evaluate_gc(model, train_dataset, args, device, name="Train")
    result_test = evaluate_gc(model, test_dataset, args, device, name="Test")
    return result_train, result_test


def gnn_preds_gc(model, dataset, edge_index, args, device, max_num_examples=None):
    model.eval()
    pred_labels = []
    ypreds = []
    for i in range(len(dataset)):
        data = dataset[i]
        h0 = Variable(torch.Tensor(data["feats"])).to(device)
        edges = Variable(torch.LongTensor(edge_index[i])).to(device)
        ypred = model(h0, edges)
        _, indices = torch.max(ypred, 1)
        pred_labels.append(indices.cpu().data.numpy())
        ypreds.append(ypred.cpu().data.numpy())
    ypreds = np.concatenate(ypreds)
    return ypreds


def gnn_preds_gc_batch(model, dataset, edge_index_set, args, device, max_num_examples=None, **kwargs):
    model.eval()
    labels = []
    pred_labels = []
    ypreds = []
    for batch_idx, data in enumerate(dataset):
        h0 = Variable(data["feats"].float()).to(device)
        labels.append(data["label"].long().numpy())
        batch_num_nodes = data["num_nodes"].int().numpy()
        assign_input = Variable(data["assign_feats"].float(), requires_grad=False).to(device)
        if "edge_masks_set" in kwargs:
            ypred = model(
                h0,
                edge_index_set[batch_idx],
                batch_num_nodes=batch_num_nodes,
                edge_weight=kwargs["edge_masks_set"][batch_idx],
                assign_x=assign_input,
            )
        else:
            ypred = model(
                h0, edge_index_set[batch_idx], batch_num_nodes=batch_num_nodes, edge_weight=None, assign_x=assign_input
            )
        _, indices = torch.max(ypred, 1)
        pred_labels.append(indices.cpu().data.numpy())
        ypreds.append(ypred.cpu().data.numpy())

        if max_num_examples is not None:
            if (batch_idx + 1) * args.batch_size > max_num_examples:
                break

    labels = np.hstack(labels)
    pred_labels = np.hstack(pred_labels)
    ypreds = np.concatenate(ypreds)
    return ypreds


def evaluate_gc(model, dataset, args, device, name="Validation", max_num_examples=None):
    model.eval()

    labels = []
    preds = []
    for batch_idx, data in enumerate(dataset):
        adj = Variable(data["adj"].float(), requires_grad=False).to(device)
        h0 = Variable(data["feats"].float()).to(device)
        labels.append(data["label"].long().numpy())
        batch_num_nodes = data["num_nodes"].int().numpy()
        assign_input = Variable(data["assign_feats"].float(), requires_grad=False).to(device)

        edge_index = []
        for a in adj:
            edges, _ = from_adj_to_edge_index(a)
            edge_index.append(edges)

        ypred = model(h0, edge_index, batch_num_nodes, assign_x=assign_input)
        _, indices = torch.max(ypred, 1)
        preds.append(indices.cpu().data.numpy())

        if max_num_examples is not None:
            if (batch_idx + 1) * args.batch_size > max_num_examples:
                break

    labels = np.hstack(labels)
    preds = np.hstack(preds)

    result = {
        "prec": metrics.precision_score(labels, preds, average="macro"),
        "recall": metrics.recall_score(labels, preds, average="macro"),
        "acc": metrics.accuracy_score(labels, preds),
    }
    print(name, " accuracy:", result["acc"])
    return result
