"""
02_kmeans_scratch.py — KMeans from Scratch (NumPy only, no scikit-learn)
=========================================================================
Purpose:
    Implement KMeans without scikit-learn to demonstrate understanding of
    the algorithm at the mathematical level, not just API usage.

Why build it manually?
    Anyone can call sklearn.cluster.KMeans(). A manual implementation proves:
      • What "initialisation" means and why random restarts matter
      • The E-step: assign each point to its nearest centroid (Euclidean)
      • The M-step: recompute centroids as the mean of assigned points
      • Why convergence is not guaranteed to be the global optimum
      • How to measure cluster quality (silhouette score, also from scratch)
    This is a deliberate portfolio differentiator for interviews where
    "walk me through the algorithm" is a standard question.

Algorithm: Lloyd's algorithm
    1. Initialise K centroids (random sample from data points)
    2. E-step: assign each point to nearest centroid
    3. M-step: recompute each centroid as mean of its cluster
    4. Repeat until convergence (centroid shift < tol) or max_iter reached
    5. Repeat N times (n_init), keep the run with lowest inertia

Imported by: 03_segmentation.py, 05_validation.py
"""

import numpy as np


# ══════════════════════════════════════════════════════════════════════════════
# Distance computation
# ══════════════════════════════════════════════════════════════════════════════

def euclidean_distances(X, centroids):
    """
    Vectorised Euclidean distance from every point in X to every centroid.

    Why vectorised?
        A Python loop over 4,000 × K at every iteration is ~100× slower.
        The broadcast formula uses the identity:
            ||x − c||² = ||x||² + ||c||² − 2·x·cᵀ
        which maps to three NumPy ops: no Python-level iteration.

    Args:
        X         : (n, d) feature matrix
        centroids : (K, d) centroid matrix

    Returns:
        distances : (n, K) — row i = distances from point i to all K centroids
    """
    X_sq  = np.sum(X**2, axis=1, keepdims=True)          # (n, 1)
    C_sq  = np.sum(centroids**2, axis=1, keepdims=True).T # (1, K)
    cross = X @ centroids.T                               # (n, K)
    dist_sq = X_sq + C_sq - 2 * cross
    return np.sqrt(np.maximum(dist_sq, 0.0))              # clip float noise


# ══════════════════════════════════════════════════════════════════════════════
# E-step and M-step
# ══════════════════════════════════════════════════════════════════════════════

def assign_clusters(X, centroids):
    """
    E-step: assign every point to its nearest centroid.

    Returns:
        labels : (n,) integer array — index of nearest centroid per point
    """
    return np.argmin(euclidean_distances(X, centroids), axis=1)


def update_centroids(X, labels, K):
    """
    M-step: recompute each centroid as the mean of all points assigned to it.

    Why handle empty clusters?
        If a centroid drifts far from all points, it may receive zero
        assignments. Taking the mean of zero points is undefined.
        Fix: reinitialise empty centroids to a random data point.
        This is a standard practical fix — not mathematically elegant,
        but it prevents the algorithm from silently returning K-1 clusters.

    Returns:
        new_centroids : (K, d)
    """
    d = X.shape[1]
    new_centroids = np.zeros((K, d))
    for k in range(K):
        mask = labels == k
        if mask.sum() == 0:
            new_centroids[k] = X[np.random.randint(len(X))]  # reinitialise
        else:
            new_centroids[k] = X[mask].mean(axis=0)
    return new_centroids


def compute_inertia(X, labels, centroids):
    """
    Inertia = Σ ||x − centroid(x)||²  (within-cluster sum of squares)

    Lower inertia → tighter, more compact clusters.
    Used for:
        (a) Elbow method: plot inertia vs K, look for the "kink"
        (b) Comparing random restarts: keep the run with the lowest inertia
    """
    total = 0.0
    for k in range(len(centroids)):
        mask = labels == k
        if mask.sum() > 0:
            total += ((X[mask] - centroids[k])**2).sum()
    return total


# ══════════════════════════════════════════════════════════════════════════════
# Full KMeans with multiple restarts
# ══════════════════════════════════════════════════════════════════════════════

def kmeans(X, K, n_init=20, max_iter=300, tol=1e-6, random_state=42):
    """
    KMeans clustering with n_init random restarts.

    Why multiple restarts?
        KMeans converges to LOCAL optima. Different starting centroids can
        yield different final clusters. By running n_init times and keeping
        the lowest-inertia solution, we substantially reduce the chance of
        returning a poor local minimum.
        n_init=20 is the sklearn default; 10 is often sufficient.

    Args:
        X             : (n, d) scaled feature matrix — MUST be pre-standardised
        K             : number of clusters
        n_init        : number of independent random restarts
        max_iter      : max iterations per run
        tol           : convergence threshold on centroid movement
        random_state  : seed for reproducibility

    Returns:
        best_labels    : (n,)    cluster assignments from the best run
        best_centroids : (K, d)  centroids from the best run
        best_inertia   : float
        best_history   : list[float]  inertia per iteration (convergence curve)
    """
    rng = np.random.default_rng(random_state)

    best_labels    = None
    best_centroids = None
    best_inertia   = np.inf
    best_history   = []

    for _ in range(n_init):
        # Random initialisation: sample K unique data points as starting centroids.
        # (K-means++ would be faster to converge but requires more code;
        #  random init + many restarts produces equivalent final quality.)
        init_idx  = rng.choice(len(X), size=K, replace=False)
        centroids = X[init_idx].copy()
        labels    = None
        history   = []

        for _ in range(max_iter):
            new_labels    = assign_clusters(X, centroids)
            new_centroids = update_centroids(X, new_labels, K)
            inertia       = compute_inertia(X, new_labels, new_centroids)
            history.append(inertia)

            # Convergence check: max centroid displacement this iteration
            shift = np.sqrt(((new_centroids - centroids)**2).sum(axis=1)).max()
            centroids = new_centroids
            labels    = new_labels

            if shift < tol:
                break   # converged

        if inertia < best_inertia:
            best_inertia   = inertia
            best_labels    = labels.copy()
            best_centroids = centroids.copy()
            best_history   = history[:]

    return best_labels, best_centroids, best_inertia, best_history


# ══════════════════════════════════════════════════════════════════════════════
# Silhouette score (from scratch, O(n²) — subsampled for speed)
# ══════════════════════════════════════════════════════════════════════════════

def silhouette_score_manual(X, labels, sample_size=500, random_state=0):
    """
    Silhouette score without scikit-learn.

    Measures how well-separated the clusters are. Range: −1 to +1.
        +1 : each point is much closer to its own cluster than any other
         0 : clusters overlap
        −1 : points appear to be in the wrong cluster

    For each point i:
        a(i) = mean distance to other points in the SAME cluster
        b(i) = mean distance to points in the NEAREST OTHER cluster
        s(i) = (b(i) − a(i)) / max(a(i), b(i))
    Overall score = mean of s(i) across all points.

    Why subsample?
        Computing all pairwise distances is O(n²). For n=4,000 that's 16M
        distance calculations — slow but feasible. We subsample to 500 by
        default for speed during K-selection sweeps; set sample_size=None
        for the final validation score.

    Args:
        X           : (n, d) scaled feature matrix (same as passed to kmeans)
        labels      : (n,) cluster assignments
        sample_size : number of points to subsample (None = all)

    Returns:
        float: mean silhouette score
    """
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2:
        return 0.0

    n = len(X)
    if sample_size and sample_size < n:
        rng = np.random.default_rng(random_state)
        idx = rng.choice(n, size=sample_size, replace=False)
        X_s, L_s = X[idx], labels[idx]
    else:
        X_s, L_s = X, labels

    scores = []
    for i in range(len(X_s)):
        k_i   = L_s[i]
        mask_same = L_s == k_i

        # a(i): mean distance to own cluster (exclude self)
        same_pts = X_s[mask_same]
        if len(same_pts) <= 1:
            scores.append(0.0)
            continue
        d_same = euclidean_distances(X_s[[i]], same_pts)[0]
        a_i = d_same.sum() / (len(same_pts) - 1)  # exclude self

        # b(i): min mean distance to any other cluster
        b_i = np.inf
        for k_other in unique_labels:
            if k_other == k_i:
                continue
            other_pts = X_s[L_s == k_other]
            if len(other_pts) == 0:
                continue
            b_candidate = euclidean_distances(X_s[[i]], other_pts)[0].mean()
            b_i = min(b_i, b_candidate)

        if np.isinf(b_i):
            scores.append(0.0)
        else:
            scores.append((b_i - a_i) / max(a_i, b_i))

    return float(np.mean(scores))


# ══════════════════════════════════════════════════════════════════════════════
# K-selection helper
# ══════════════════════════════════════════════════════════════════════════════

def elbow_and_silhouette(X, k_range=range(2, 9), n_init=10, random_state=42):
    """
    Run KMeans for a range of K values; return inertia + silhouette per K.

    Why two metrics for K selection?
        The elbow method (inertia) can be ambiguous — the "kink" is not
        always sharp. Silhouette provides an independent validation signal.
        When both methods agree on the same K, confidence is high.

    Returns:
        list of dicts: [{"K": k, "inertia": float, "silhouette": float}, ...]
    """
    results = []
    for K in k_range:
        labels, centroids, inertia, _ = kmeans(
            X, K=K, n_init=n_init, random_state=random_state
        )
        sil = silhouette_score_manual(X, labels)
        results.append({"K": K, "inertia": inertia, "silhouette": sil})
        print(f"  K={K}  inertia={inertia:>10.1f}  silhouette={sil:.4f}")
    return results
