# ⚡ GUIA RÁPIDO & SUPER FORMULÁRIO DE P3 (FÍSICA II — UFF)

> **Como usar:** Resolva as primeiras provas consultando este resumo teórico. Depois, passe a usar apenas o **Formulário Oficial da P3** (mesma folha que vem na página 2 da prova real).

---

## 📌 1. INDUÇÃO ELETROMAGNÉTICA (FARADAY & LENZ)

* **Fluxo Magnético:**
  $$\Phi_B = \int \vec{B} \cdot d\vec{A} = B A \cos\theta \quad (\text{se } \vec{B} \text{ uniforme e superfície plana})$$
* **Lei de Faraday (para $N$ espiras):**
  $$\mathcal{E} = -N \frac{d\Phi_B}{dt}$$
* **Lei de Lenz (Sentido da Corrente Induzida):**
  * A corrente induzida gera um campo magnético $\vec{B}_{\text{ind}}$ que **se opõe à variação** do fluxo $\Delta\Phi_B$:
    * Fluxo **aumentando** $\implies \vec{B}_{\text{ind}}$ aponta **contra** $\vec{B}_{\text{ext}}$.
    * Fluxo **diminuindo** $\implies \vec{B}_{\text{ind}}$ aponta **no mesmo sentido** de $\vec{B}_{\text{ext}}$.
  * Use a Regra da Mão Direita no $\vec{B}_{\text{ind}}$ (polegar em $\vec{B}_{\text{ind}}$ $\implies$ dedos dão o sentido horário/anti-horário da corrente induzida).
* **FEM de Movimento (barra condutora de comprimento $\ell$ em $\vec{B}$ uniforme):**
  $$\mathcal{E} = B \ell v \qquad I = \frac{B \ell v}{R} \qquad F_{\text{ext}} = F_B = I \ell B = \frac{B^2 \ell^2 v}{R} \qquad P = \frac{B^2 \ell^2 v^2}{R}$$
* **Campo Elétrico Induzido (Lei de Faraday na forma integral):**
  $$\oint \vec{E} \cdot d\vec{s} = -\frac{d\Phi_B}{dt}$$
  * Para região cilíndrica de raio $R$ com $B(t)$ variando uniformemente:
    * Dentro ($r < R$): $E = \frac{r}{2} \left|\frac{dB}{dt}\right|$
    * Fora ($r > R$): $E = \frac{R^2}{2r} \left|\frac{dB}{dt}\right|$

---

## 📌 2. INDUTÂNCIA, ENERGIA MAGNÉTICA & CIRCUITOS RL

* **Indutância ($L$):**
  $$L = \frac{N \Phi_B}{I} \qquad \mathcal{E}_L = -L \frac{dI}{dt}$$
  * **Solenoide ideal** de $N$ espiras, área $A$ e comprimento $\ell$:
    $$L = \mu_0 n^2 A \ell = \frac{\mu_0 N^2 A}{\ell}$$
* **Energia Armazenada no Indutor & Densidade de Energia Magnética:**
  $$U_L = \frac{1}{2} L I^2 \qquad u_B = \frac{B^2}{2\mu_0}$$
* **Circuito RL (Constante de tempo $\tau = \frac{L}{R}$):**
  * **Crescimento de corrente (chave fechada com fonte $\mathcal{E}$):**
    $$I(t) = \frac{\mathcal{E}}{R}\left(1 - e^{-t/\tau}\right)$$
  * **Decaimento de corrente (sem fonte, a partir de $I_0$):**
    $$I(t) = I_0 e^{-t/\tau}$$

> 💡 **Regra de Ouro em Circuitos RL (MUITO COBRADO NA P3):**
> * **Em $t = 0^+$ (chave recém-fechada):** o indutor se opõe à variação brusca de corrente e age como uma **CHAVE ABERTA** ($I_L = 0$).
> * **Em $t \to \infty$ (regime estacionário):** $dI/dt = 0$, logo $V_L = 0$; o indutor age como um **FIO / CURTO-CIRCUITO**.

---

## 📌 3. OSCILAÇÕES ELETROMAGNÉTICAS (CIRCUITO LC)

* **Frequência angular natural:**
  $$\omega_0 = \frac{1}{\sqrt{LC}} \qquad f_0 = \frac{1}{2\pi\sqrt{LC}} \qquad T = 2\pi\sqrt{LC}$$
* **Carga e Corrente (partindo de $Q_0$ em $t=0$):**
  $$q(t) = Q_0 \cos(\omega_0 t) \qquad i(t) = -\omega_0 Q_0 \operatorname{sen}(\omega_0 t) \implies I_{\max} = \omega_0 Q_0$$
* **Conservação de Energia (sem resistência):**
  $$U_{\text{total}} = U_E + U_B = \frac{q^2}{2C} + \frac{1}{2} L i^2 = \frac{Q_0^2}{2C} = \frac{1}{2} L I_{\max}^2$$
  * Quando $q = 0$, toda a energia está no **indutor** ($i = I_{\max}$).
  * Quando $i = 0$, toda a energia está no **capacitor** ($q = Q_0$).

---

## 📌 4. CORRENTE ALTERNADA (CA), FASORES & CIRCUITO RLC EM SÉRIE

* **Fonte CA:** $\mathcal{E}(t) = \mathcal{E}_0 \cos(\omega t)$ com $\omega = 2\pi f = \frac{2\pi}{T}$.
* **Reatâncias:**
  $$X_L = \omega L \qquad X_C = \frac{1}{\omega C}$$
* **Relações de Fase (regra mnemônica ELI / ICE):**
  * **Resistor ($R$):** $V_R$ e $I$ estão **em fase** ($\phi = 0$).
  * **Indutor ($L$):** $V_L$ está **$90^\circ$ ($+\pi/2$) adiantada** em relação à corrente $I$ (ou $I$ atrasada de $\pi/2$).
  * **Capacitor ($C$):** $V_C$ está **$90^\circ$ ($-\pi/2$) atrasada** em relação à corrente $I$ (ou $I$ adiantada de $\pi/2$).
* **Impedância ($Z$) e Corrente de Pico ($I_0$):**
  $$Z = \sqrt{R^2 + (X_L - X_C)^2} \qquad I_0 = \frac{\mathcal{E}_0}{Z} \qquad i(t) = I_0 \cos(\omega t - \phi)$$
* **Ângulo de Fase ($\phi$):**
  $$\tan\phi = \frac{X_L - X_C}{R} \qquad \cos\phi = \frac{R}{Z}$$
  * $X_L > X_C \implies \phi > 0$ (circuito **indutivo**, altas frequências).
  * $X_C > X_L \implies \phi < 0$ (circuito **capacitivo**, baixas frequências).
* **Ressonância ($\omega = \omega_0 = \frac{1}{\sqrt{LC}}$):**
  * $X_L = X_C \implies Z = Z_{\min} = R$, $\phi = 0$, $\cos\phi = 1$, corrente **máxima** e em fase com $\mathcal{E}$.
  * Atenção: na ressonância $V_L = V_C$ podem ser maiores que $\mathcal{E}_0$, mas se cancelam vetorialmente!
* **Valores Eficazes (RMS) e Potência Média:**
  $$x_{\text{rms}} = \frac{x_{\max}}{\sqrt{2}}$$
  $$P_{\text{med}} = I_{\text{rms}} \mathcal{E}_{\text{rms}} \cos\phi = I_{\text{rms}}^2 R = \frac{\mathcal{E}_{\text{rms}}^2 R}{Z^2}$$
  *(Somente o **resistor** dissipa potência média; indutores e capacitores ideais têm $P_{\text{med}} = 0$.)*

---

## 📌 5. REVISÃO DE MAGNETISMO (SEMPRE CAI NA P3 DA UFF!)

* **Força Magnética:** $\vec{F}_B = q(\vec{v} \times \vec{B})$, $\vec{F}_{\text{fio}} = I(\vec{\ell} \times \vec{B})$.
  * Raio em MCU ($\vec{v}\perp\vec{B}$): $R = \frac{mv}{|q|B}$ | Período do cíclotron: $T = \frac{2\pi m}{|q|B}$.
  * Seletor de velocidades: $v = \frac{E}{B}$.
* **Fontes de Campo Magnético ($\mu_0 = 4\pi \times 10^{-7}\text{ T}\cdot\text{m/A}$):**
  * Fio reto infinito: $B = \frac{\mu_0 I}{2\pi d}$
  * Arco circular (ângulo $\varphi$ em rad): $B = \frac{\mu_0 I \varphi}{4\pi R}$
  * Solenoide ideal: $B = \mu_0 n I = \frac{\mu_0 N I}{\ell}$
  * Fio cilíndrico maciço ($r < R$): $B = \frac{\mu_0 I r}{2\pi R^2}$
  * Força entre fios paralelos: $\frac{F}{L} = \frac{\mu_0 I_1 I_2}{2\pi d}$ (mesmo sentido = **atração**; opostos = **repulsão**).
* **Lei de Ampère-Maxwell & Corrente de Deslocamento:**
  $$\oint \vec{B} \cdot d\vec{s} = \mu_0 (I_{\text{env}} + i_d) \qquad i_d = \varepsilon_0 \frac{d\Phi_E}{dt}$$
  * Entre as placas de um capacitor carregando/descarregando: $i_d = i_{\text{condução}}$ (total) e para raio $r < R$: $i_{d,\text{env}} = i \frac{r^2}{R^2}$.
* **Lei de Gauss do Magnetismo:** $\oint \vec{B} \cdot d\vec{A} = 0$ (não existem monopolos magnéticos; cortar um ímã ao meio gera dois novos ímãs com Norte e Sul).
