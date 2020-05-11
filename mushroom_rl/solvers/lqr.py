import numpy as np


def solve_lqr_linear(lqr, max_iterations=100):
    A, B, Q, R, gamma = _parse_lqr(lqr)

    P = np.eye(Q.shape[0])
    K = _compute_riccati_gain(P, A, B, R, gamma)

    it = 0
    while it < max_iterations:
        P = _compute_riccati_rhs(A, B, Q, R, gamma, K, P)
        K = _compute_riccati_gain(P, A, B, R, gamma)

        it += 1

    return K


def compute_lqr_P(lqr, K):
    A, B, Q, R, gamma = _parse_lqr(lqr)

    L, M = _compute_lqr_intermediate_results(K, A, B, Q, R, gamma)

    vec_P = np.linalg.solve(M, L.reshape(-1))

    return vec_P.reshape(Q.shape)


def compute_lqr_V(x, lqr, K):
    P = compute_lqr_P(lqr, K)
    return -x.T @ P @ x


def compute_lqg_V(x, lqr, K, Sigma):
    P = compute_lqr_P(lqr, K)
    A, B, Q, R, gamma = _parse_lqr(lqr)
    return -x.T @ P @ x - np.trace(Sigma @ (R + gamma*B.T @ P @ B)) / (1.0 - gamma)


def compute_lqr_Q_matrix(lqr, K):
    A, B, Q, R, gamma = _parse_lqr(lqr)
    P = compute_lqr_P(lqr, K)

    M = np.block([[Q + gamma * A.T @ P @ A, gamma * A.T @ P @ B],
                  [gamma * B.T @ P @ A, R + gamma * B.T @ P @ B]])

    return M


def compute_lqg_Q_additional_term(lqr, K, Sigma):
    A, B, Q, R, gamma = _parse_lqr(lqr)
    P = compute_lqr_P(lqr, K)
    b = gamma/(1-gamma)*np.trace(Sigma @ (R + gamma * B.T @ P @ B))
    return b


def compute_lqr_Q(x, lqr, K):
    """
    x is a (state,action) pair.
    """
    M = compute_lqr_Q_matrix(lqr, K)
    return -x.T @ M @ x


def compute_lqg_Q(x, lqr, K, Sigma):
    """
    x is a (state,action) pair.
    """
    M = compute_lqr_Q_matrix(lqr, K)
    b = compute_lqg_Q_additional_term(lqr, K, Sigma)
    return -x.T @ M @ x - b


def compute_lqg_gradient(x, lqr, K, Sigma):
    A, B, Q, R, gamma = _parse_lqr(lqr)
    L, M = _compute_lqr_intermediate_results(K, A, B, Q, R, gamma)

    Minv = np.linalg.inv(M)

    n_elems = K.shape[0]*K.shape[1]
    dJ = np.zeros(n_elems)
    for i in range(n_elems):
        dLi, dMi = _compute_lqr_intermediate_results_diff(K, A, B, R, gamma, i)

        vec_dPi = -Minv @ dMi @ Minv @ L.reshape(-1) + np.linalg.solve(M, dLi.reshape(-1))

        dPi = vec_dPi.reshape(Q.shape)

        dJ[i] = (x.T @ dPi @ x).item() + gamma*np.trace(Sigma @ B.T @ dPi @ B)/(1.0-gamma)

    return -dJ


def _parse_lqr(lqr):
    return lqr.A, lqr.B, lqr.Q, lqr.R, lqr.info.gamma


def _compute_riccati_rhs(A, B, Q, R, gamma, K, P):
    return Q + gamma*(A.T @ P @ A - K.T @ B.T @ P @ A - A.T @ P @ B @ K + K.T @ B.T @ P @ B @ K) \
           + K.T @ R @ K


def _compute_riccati_gain(P, A, B, R, gamma):
    return gamma * np.linalg.inv((R + gamma * (B.T @ P @ B))) @ B.T @ P @ A


def _compute_lqr_intermediate_results(K, A, B, Q, R, gamma):
    size = Q.shape[0] ** 2

    L = Q + K.T @ R @ K
    kb = K.T @ B.T
    M = np.eye(size, size) - gamma * (np.kron(A.T, A.T) - np.kron(A.T, kb) - np.kron(kb, A.T) + np.kron(kb, kb))

    return L, M


def _compute_lqr_intermediate_results_diff(K, A, B, R, gamma, i):
    n_elems = K.shape[0]*K.shape[1]
    vec_dKi = np.zeros(n_elems)
    vec_dKi[i] = 1
    dKi = vec_dKi.reshape(K.shape)
    kb = K.T @ B.T
    dkb = dKi.T @ B.T

    dL = dKi.T @ R @ K + K.T @ R @ dKi
    dM = gamma * (np.kron(A.T, dkb) + np.kron(dkb, A.T) - np.kron(dkb, kb) - np.kron(kb, dkb))

    return dL, dM
