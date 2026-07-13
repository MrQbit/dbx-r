"""Shared helpers for Open3D registration of action-figure pieces to the statue."""
import os, numpy as np, trimesh, open3d as o3d
from scipy.spatial import cKDTree

BASE = "/home/mrqbit/Downloads/dbx-r/reference/self_print_rocky/rocky-statue-figure-files"
AF = os.path.join(BASE, "Action_figure_Unsupported_STLS")
STATUE_PATH = os.path.join(BASE, "statue_unsupported", "statue_unsupported.stl")
OUT = "/tmp/claude-1000/-home-mrqbit-Downloads-dbx-r/e0785d70-49cd-4364-ac85-d5cf693b249e/scratchpad"

PIECES = ["torso", "1-A", "1-C", "2-A", "2-B", "3-A", "3-B", "4-A", "4-B", "5-A", "5-B"]
LEG_A = ["1-A", "2-A", "3-A", "4-A", "5-A"]  # thighs (hip-socket + knee-ball)
LEG_B = ["2-B", "3-B", "4-B", "5-B"]         # feet (knee-socket)


def load_trimesh(name):
    if name == "statue":
        p = STATUE_PATH
    else:
        p = os.path.join(AF, name + ".stl")
    return trimesh.load(p, process=False)


def tm_to_pcd(tm, n_points, seed=0):
    """Sample a trimesh surface -> o3d point cloud."""
    rng = np.random.RandomState(seed)
    pts, _ = trimesh.sample.sample_surface(tm, n_points, seed=seed)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(pts))
    return pcd


def preprocess(pcd, voxel):
    down = pcd.voxel_down_sample(voxel)
    down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 2.0, max_nn=30))
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        down, o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 5.0, max_nn=100))
    return down, fpfh


def global_ransac(src_d, src_f, tgt_d, tgt_f, voxel, seed=None):
    dist = voxel * 1.5
    if seed is not None:
        o3d.utility.random.seed(seed)
    res = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        src_d, tgt_d, src_f, tgt_f, True, dist,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False), 4,
        [o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
         o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(dist)],
        o3d.pipelines.registration.RANSACConvergenceCriteria(400000, 0.999))
    return res


def _apply(T, P):
    return (P @ T[:3, :3].T) + T[:3, 3]


def _metrics(src_pts, tree, T, thr):
    """o3d-compatible fitness (fraction of src with NN<thr) and inlier_rmse."""
    d, _ = tree.query(_apply(T, src_pts))
    inl = d < thr
    n = int(inl.sum())
    fitness = n / len(src_pts)
    rmse = float(np.sqrt((d[inl] ** 2).mean())) if n else 0.0
    return fitness, rmse, n


def icp_manual(src_pts, tgt_pts, tgt_nrm, init, voxel, p2plane=True):
    """Point-to-plane ICP (point-to-point fallback) implemented with scipy KDTree,
    because registration_icp segfaults in this Open3D 0.18 aarch64 build.
    Returns (T, fitness, inlier_rmse) with o3d-compatible metric definitions."""
    tree = cKDTree(tgt_pts)
    T = np.asarray(init, dtype=float).copy()
    for mult in (3.0, 2.0, 1.5, 1.5, 1.5):
        thr = voxel * mult
        for _ in range(25):
            S = _apply(T, src_pts)
            d, idx = tree.query(S)
            inl = d < thr
            if inl.sum() < 10:
                break
            S_i = S[inl]
            Q_i = tgt_pts[idx[inl]]
            if p2plane and tgt_nrm is not None:
                N_i = tgt_nrm[idx[inl]]
                # linearized point-to-plane: solve 6x6 for [alpha,beta,gamma,tx,ty,tz]
                c = np.cross(S_i, N_i)
                A = np.hstack([c, N_i])                 # (m,6)
                b = -np.sum((S_i - Q_i) * N_i, axis=1)  # (m,)
                try:
                    x = np.linalg.solve(A.T @ A, A.T @ b)
                except np.linalg.LinAlgError:
                    break
                a, bb, g = x[:3]
                dR = np.array([[1, -g, bb], [g, 1, -a], [-bb, a, 1]])
                U, _, Vt = np.linalg.svd(dR)
                dR = U @ Vt
                dt = x[3:]
                dT = np.eye(4); dT[:3, :3] = dR; dT[:3, 3] = dt
                T = dT @ T
            else:
                # point-to-point (Umeyama/Kabsch, no scale)
                mu_s = S_i.mean(0); mu_q = Q_i.mean(0)
                H = (S_i - mu_s).T @ (Q_i - mu_q)
                U, _, Vt = np.linalg.svd(H)
                D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T))
                R = Vt.T @ D @ U.T
                t = mu_q - R @ mu_s
                dT = np.eye(4); dT[:3, :3] = R; dT[:3, 3] = t
                T = dT @ T
    fitness, rmse, _ = _metrics(src_pts, tree, T, voxel * 1.5)
    return T, fitness, rmse


def icp_refine(src_d, tgt_d, init, voxel, p2plane=True):
    # coarse then fine
    T = init
    for mult in (3.0, 1.5):
        thr = voxel * mult
        if p2plane:
            est = o3d.pipelines.registration.TransformationEstimationPointToPlane()
        else:
            est = o3d.pipelines.registration.TransformationEstimationPointToPoint()
        res = o3d.pipelines.registration.registration_icp(
            src_d, tgt_d, thr, T, est,
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=80))
        T = res.transformation
    return res


def evaluate(src_d, tgt_d, T, voxel):
    return o3d.pipelines.registration.evaluate_registration(src_d, tgt_d, voxel * 1.5, T)
