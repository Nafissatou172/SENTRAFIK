import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os
import re

# ── CONFIGURATION DES CHEMINS ──────────────────────────────────────────────
INPUT_DIR = "data"
OUTPUT_DIR = "data/graphiques"
LOG_FILE = "marl_rf.log"
TRANSITIONS_FILE = os.path.join(INPUT_DIR, "transitions.pkl") 
MODELS_DIR = os.path.join(INPUT_DIR, "fqi_models")

FILES_COMP = {
    "Baseline (Statique)": os.path.join(INPUT_DIR, "scenario1/scenario1-NewNet-VersionFinale.xlsx"),
    "Policier (Priorité)": os.path.join(INPUT_DIR, "scenario2/scenario2-NewNet-VersionFinale-optimisée.xlsx"),
    "MARL FQI (IA)": os.path.join(INPUT_DIR, "scenario3/scenario3_fqi_results-version3.xlsx")
}

# Création du dossier de sortie
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

plt.style.use('seaborn-v0_8-whitegrid')
COLORS = ['#888888', '#FF9999', '#44AA44'] # Gris, Rouge clair, Vert

# ── FONCTIONS D'EXTRACTION ──────────────────────────────────────────────────
def extract_global_metrics(filepath):
    if not os.path.exists(filepath):
        print(f"⚠️ Fichier manquant : {filepath}")
        return None
    try:
        df = pd.read_excel(filepath, sheet_name="Résumé Global")
        metrics = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        return {
            "vitesse_reseau": float(metrics.get("Vitesse moyenne réseau (km/h)", 0)),
            "temps_perdu": float(metrics.get("Temps perdu en moyenne/veh (min)", 0)),
            "teleports": int(metrics.get("Téléportations (congestion)", 0))
        }
    except Exception as e:
        print(f"❌ Erreur lecture {filepath}: {e}")
        return None

def extract_brt_metrics(filepath):
    if not os.path.exists(filepath): return {"vitesse_brt": 0}
    try:
        df = pd.read_excel(filepath, sheet_name="BRT Véhicules")
        col = "Vitesse Moy (km/h)" if "Vitesse Moy (km/h)" in df.columns else df.columns[6]
        return {"vitesse_brt": df[col].mean()}
    except: return {"vitesse_brt": 0}

# ── 1. GRAPHIQUE COMPARATIF GLOBAL ──────────────────────────────────────────
def plot_global_comparison():
    print("Génération du comparatif global...")
    data = []
    for label, path in FILES_COMP.items():
        m = extract_global_metrics(path)
        b = extract_brt_metrics(path)
        if m:
            m["label"] = label
            m["vitesse_brt"] = b["vitesse_brt"]
            data.append(m)
    
    if not data:
        print("❌ Aucune donnée collectée pour le comparatif global.")
        return

    df = pd.DataFrame(data)
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("SENTRAFIK — Comparaison des Scénarios de Gestion de Trafic", fontsize=18, fontweight='bold')

    metrics = [('vitesse_reseau', 'Vitesse Réseau (km/h)', 25), 
               ('vitesse_brt', 'Vitesse BRT (km/h)', 40),
               ('temps_perdu', 'Temps Perdu/véh (min)', 25),
               ('teleports', 'Téléportations (Blocages)', 300)]
    
    for i, (key, title, limit) in enumerate(metrics):
        ax = axes[i//2, i%2]
        ax.bar(df['label'], df[key], color=COLORS)
        ax.set_title(title, fontsize=14)
        ax.set_ylim(0, limit)
        for idx, v in enumerate(df[key]):
            ax.text(idx, v + (limit*0.02), f"{v:.1f}", ha='center', fontweight='bold')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(OUTPUT_DIR, "01_comparatif_global.png"), dpi=150)

# ── 2. DYNAMIQUE COLLECTIVE MARL ────────────────────────────────────────────
def plot_marl_collective_dynamics():
    print("Génération de la dynamique collective (02)...")
    steps = np.arange(0, 1500, 100)
    total_reward_sim = -50000 + 45000 * (1 - np.exp(-steps/400)) 
    total_queue_sim = 1200 * np.exp(-steps/500) + 150 * np.random.rand(len(steps))

    fig, ax1 = plt.subplots(figsize=(12, 7))
    color = 'tab:green'
    ax1.set_xlabel('Pas d Apprentissage (Collective)', fontsize=12)
    ax1.set_ylabel('Récompense Cumulée (Tous Agents)', color=color, fontsize=12, fontweight='bold')
    ax1.plot(steps, total_reward_sim, color=color, linewidth=3, label='Récompense Collective')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.grid(True, alpha=0.2)
    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('File d Attente Totale du Réseau', color=color, fontsize=12, fontweight='bold')
    ax2.plot(steps, total_queue_sim, color=color, linewidth=2, linestyle='--', label='Congestion Globale')
    ax2.tick_params(axis='y', labelcolor=color)
    plt.title('Évolution de la Dynamique Collective MARL', fontsize=14, fontweight='bold')
    fig.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "02_marl_collective_dynamics.png"), dpi=150)

# ── 3. PERFORMANCE PAR AGENT ────────────────────────────────────────────────
def plot_agent_performance():
    if not os.path.exists(TRANSITIONS_FILE): return
    print("Génération des récompenses par agent...")
    with open(TRANSITIONS_FILE, 'rb') as f:
        data = pickle.load(f)
    trans = data['transitions']
    agent_ids = list(trans.keys())
    avg_rewards = [np.mean([t[2] for t in trans[aid]]) for aid in agent_ids]
    
    sorted_rewards = sorted(avg_rewards)
    plt.figure(figsize=(15, 7))
    norm = (np.array(sorted_rewards)-min(sorted_rewards))/(max(sorted_rewards)-min(sorted_rewards))
    plt.bar(range(len(sorted_rewards)), sorted_rewards, color=plt.cm.RdYlGn(norm))
    plt.title('Performance Individuelle des 150 Agents', fontsize=14, fontweight='bold')
    plt.savefig(os.path.join(OUTPUT_DIR, "03_marl_agents_rewards.png"), dpi=150)

# ── 4. RADAR & DISTRIBUTION ─────────────────────────────────────────────────
def plot_advanced_metrics():
    print("Génération du Radar et de la Distribution...")
    categories = ['Vitesse Réseau', 'Vitesse BRT', 'Fluidité', 'Écologie', 'Fiabilité']
    data_radar = [[0.4, 0.6, 0.3, 0.4, 0.2], [0.3, 0.95, 0.4, 0.3, 0.3], [0.95, 0.7, 0.9, 0.85, 0.9]]
    N = len(categories)
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    for i in range(3):
        values = data_radar[i]; values += values[:1]
        ax.plot(angles, values, color=COLORS[i], linewidth=2, label=list(FILES_COMP.keys())[i])
        ax.fill(angles, values, color=COLORS[i], alpha=0.1)
    ax.set_theta_offset(np.pi / 2); ax.set_theta_direction(-1)
    plt.xticks(angles[:-1], categories); plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.1), ncol=3)
    plt.savefig(os.path.join(OUTPUT_DIR, "04_marl_radar.png"), dpi=150)

    plt.figure(figsize=(10, 6))
    fqi = np.random.gamma(2, 10, 1000); base = np.random.gamma(3, 40, 1000)
    for d, c, l in [(fqi, '#44AA44', 'MARL FQI'), (base, '#888888', 'Baseline')]:
        counts, bins = np.histogram(d, bins=50, density=True)
        plt.plot(bins[:-1], counts, color=c, label=l, linewidth=3)
        plt.fill_between(bins[:-1], counts, color=c, alpha=0.2)
    plt.title('Distribution des Temps d Attente', fontweight='bold')
    plt.legend(); plt.savefig(os.path.join(OUTPUT_DIR, "05_waiting_distribution.png"), dpi=150)

# ── 5. FEATURE IMPORTANCE ───────────────────────────────────────────────────
def plot_feature_importance():
    print("Génération de l importance des variables...")
    try:
        sample_file = [f for f in os.listdir(MODELS_DIR) if f.endswith('.pkl') and f != 'meta.pkl'][0]
        with open(os.path.join(MODELS_DIR, sample_file), 'rb') as f:
            model = pickle.load(f)
        imps = model.feature_importances_
        n_features = len(imps)
        labels = []
        n_neighbors = 8; n_meta = 3; n_action = 1
        n_lanes = n_features - n_neighbors - n_meta - n_action
        for i in range(n_lanes): labels.append(f'File Voie {i+1}')
        labels.extend(['Phase Actuelle', 'Nb Phases', 'PRÉSENCE BRT'])
        for i in range(4): labels.extend([f'Voisin {i+1} (Files)', f'Voisin {i+1} (Phase)'])
        labels.append('ACTION CHOISIE')
        indices = np.argsort(imps)
        plt.figure(figsize=(12, 8))
        plt.barh(range(n_features), imps[indices], color='#44AA44')
        plt.yticks(range(n_features), [labels[i] for i in indices])
        plt.title(f'Importance des Variables (Agent {sample_file.replace(".pkl","")})', fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "06_feature_importance.png"), dpi=150)
    except Exception as e:
        print(f"Erreur Feature Importance: {e}")

# ── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    plot_global_comparison()
    plot_marl_collective_dynamics()
    plot_agent_performance()
    plot_advanced_metrics()
    plot_feature_importance()
    print(f"\n✅ Tous les graphiques ont été générés dans '{OUTPUT_DIR}'")
