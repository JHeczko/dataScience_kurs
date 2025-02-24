$
\mu = \frac{1}{n} \sum_{i=1}^n x_i \\ \\
$

$
\text{M} = x_{\frac{n+1}{2}} \\ \\ 
\text{M} = \frac{x_{\frac{n}{2}} + x_{\frac{n}{2} + 1}}{2} \\ \\
$

$
\delta^2 = \frac{1}{n} \sum_{i=1}^n (x_i - \mu)^2 \\ \\ 
s^2 = \frac{1}{n-1} \sum_{i=1}^n (x_i - \bar{x})^2 \\ \\
$

$
\delta = \sqrt{\delta^2} \\ \\
s = \sqrt{s^2} \\ \\
$

---
$
Q_1/Q_3 -/+ 1\frac{1}{2} IQR
$

---

$
Y = \Beta_0 + \Beta_1 X + \epsilon \\
\Sigma_{i=0}^{n} (y_i - \Beta_0 + \Beta_1 X_i )^2
$

---

$
w_{new}=w_{old}-\lambda gS \\
gS = \frac{\delta F}{\delta w}
$

$
w_{t+1} = w_t - \lambda g(w_t) \\
w_{t+1} = w_t + v_{t+1} \\
v_{t+1} = p v_t - \lambda g(w_t)
$

---

$
RSS(w) + \lambda ||w||_2^2\\
RSS(w) + \lambda ||w||_1
$

---

$
NW: y_p = \frac{\Sigma_{i=1}^{N} K_\lambda (D(x_i,x_p)) y_i}{\Sigma_{i=1}^{N} K_\lambda (D(x_i,x_p))}
$

---

$Sc(x_i) = W^T h(x_i)$

$\sigma(x) = \frac{1}{1 + e^{-x}}$

---

$\mathcal{L}(\theta) = \prod_{i=1}^{N} p(x_i)^{y_i} (1 - p(x_i))^{1 - y_i}$

$\log \mathcal{L}(\theta) = \sum_{i=1}^{N} \left[ y_i \log(p(x_i)) + (1 - y_i) \log(1 - p(x_i)) \right]$

$\frac{\partial}{\partial \theta} \log \mathcal{L}(\theta) = \sum_{i=1}^{N} \left[ y_i - p(x_i) \right] x_i$

--- 

$G_i = 1 - \Sigma_{k=1}^{n} p_{i,k}^2$

---

$\hat{y} = sign (\Sigma^T_{t=1} \hat{w_{t}} f_t (x))$

---

$w_i^{(1)} = \frac{1}{N}, \quad i = 1, 2, \dots, N$

$r_j = \frac{\Sigma_{i=1, \hat{y_j^{(i)}} \neq y_j^{(i)}}^N w^(i)}{\Sigma_{i=1}^N w^(i)}$

$\alpha_j = \lambda \ln\left(\frac{1 - r_j}{r_j}\right)$

$w_i^{(t+1)} = w_i^{(t)} \exp(\alpha_j)$

$w_i^{(t+1)} = \frac{w_i^{(t+1)}}{\sum_{i=1}^{N} w_i^{(t+1)}}$

$\hat{y}(x) = argmax_k \Sigma_{j=1, \hat{y}(x) = k}^N \alpha_j$

---

$
IDF = log(\frac{num-d}{1+num-d-u-w}) \\
TFIDF = TF * IDF \\
$

$d_{\text{e}}(x, y) = \sqrt{\sum_{i=1}^{n} (x_i - y_i)^2} \\$

$d_{c}(x, y) = 1 - \frac{\sum_{i=1}^{n} x_i y_i}{\sqrt{\sum_{i=1}^{n} x_i^2} \cdot \sqrt{\sum_{i=1}^{n} y_i^2}}$

$d_{\text{m}}(x, y) = \sum_{i=1}^{n} |x_i - y_i|$


---

$z_i = argmin_j ||\mu_j - x_i||^2_2$

$\mu_j = argmin_{\mu} \Sigma_{i:z_i = j} x_i$

---

$
\mathcal{L}(\Theta) = \prod_{i=1}^{N} \sum_{k=1}^{K} \pi_k \cdot p(x_i | \theta_k)
$

$\gamma_{ik} = \frac{\pi_k \cdot p(x_i | \theta_k)}{\sum_{j=1}^{K} \pi_j \cdot p(x_i | \theta_j)}$

$\pi_k = \frac{\sum_{i=1}^{N} \gamma_{ik}}{N}$

$\mu_k = \frac{\sum_{i=1}^{N} \gamma_{ik} \cdot x_i}{\sum_{i=1}^{N} \gamma_{ik}}$

$\Sigma_k = \frac{\sum_{i=1}^{N} \gamma_{ik} \cdot (x_i - \mu_k)(x_i - \mu_k)^\top}{\sum_{i=1}^{N} \gamma_{ik}}$
---

$acc = \frac{TP}{ALL}$

$rc = \frac{TP}{TP+FN}$

---

$R^2 = 1 - \frac{SS_{res}}{SS_{tot}}$

---

$\bar{x} \pm z^* \frac{s}{\sqrt{n}}$

---