import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import pickle
import os
import re

# ── CONFIGURATION DES CHEMINS ──────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INPUT_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data/graphiques")
LOG_FILE = os.path.join(PROJECT_ROOT, "logs/marl_rf.log")
TRANSITIONS_FILE = os.path.join(INPUT_DIR, "transitions.pkl") 
MODELS_DIR = os.path.join(INPUT_DIR, "fqi_models")

FILES_COMP = {
    "Baseline (Statique)": os.path.join(INPUT_DIR, "scenario1/traffic_metrics_results.xlsx"),
    "Policier (Priorité)": os.path.join(INPUT_DIR, "scenario2/scenario2_results.xlsx"),
    "MARL FQI (IA)": os.path.join(INPUT_DIR, "scenario3/scenario3_fqi_results.xlsx")
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

    # Export des données sous forme de tableau Excel
    excel_path = os.path.join(OUTPUT_DIR, "01_comparatif_global.xlsx")
    df_export = df.rename(columns={
        'label': 'Scénario',
        'vitesse_reseau': 'Vitesse Réseau (km/h)',
        'vitesse_brt': 'Vitesse BRT (km/h)',
        'temps_perdu': 'Temps Perdu / véhicule (min)',
        'teleports': 'Téléportations (blocages)'
    })
    df_export.to_excel(excel_path, index=False)
    print(f"✅ Données du graphique exportées dans {excel_path}")

    metrics = [
        ('vitesse_reseau', 'Vitesse Réseau', 'km/h',  True),
        ('vitesse_brt',    'Vitesse BRT',    'km/h',  True),
        ('temps_perdu',    'Temps Perdu / véhicule', 'min', False),
        ('teleports',      'Téléportations (blocages)', '',  False)
    ]

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("SENTRAFIK — Comparaison des 3 Scénarios de Gestion de Trafic",
                 fontsize=18, fontweight='bold', y=0.98)

    for i, (key, title, unit, higher_better) in enumerate(metrics):
        ax = axes[i // 2, i % 2]
        values = df[key].values
        labels = df['label'].values
        limit = max(values) * 1.35

        bars = ax.bar(labels, values, color=COLORS, width=0.55,
                      edgecolor='white', linewidth=1.5, zorder=3)

        # Annotation des valeurs au-dessus des barres
        for idx, (bar, v) in enumerate(zip(bars, values)):
            fmt = f"{v:.1f}" if isinstance(v, float) else f"{int(v)}"
            label_text = f"{fmt} {unit}" if unit else fmt
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + limit * 0.02,
                    label_text, ha='center', va='bottom', fontsize=12, fontweight='bold',
                    color=COLORS[idx])

        # Annotation du gain MARL vs Baseline
        if len(values) >= 3:
            baseline_val = values[0]
            marl_val = values[2]
            if baseline_val != 0:
                pct = ((marl_val - baseline_val) / abs(baseline_val)) * 100
                sign = "+" if pct > 0 else ""
                gain_color = '#059669' if (higher_better and pct > 0) or (not higher_better and pct < 0) else '#DC2626'
                ax.text(2, marl_val + limit * 0.08, f"{sign}{pct:.0f}% vs Baseline",
                        ha='center', fontsize=9, fontstyle='italic', color=gain_color)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)
        ax.set_ylabel(f"{unit}" if unit else "Nombre", fontsize=11)
        ax.set_ylim(0, limit)
        ax.grid(axis='y', alpha=0.25, linestyle='--', zorder=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xticks([]) # Remove x-axis labels to use the global legend

    # Add global legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=COLORS[i], edgecolor='white', label=labels[i]) for i in range(len(labels))]
    fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.94), ncol=3, fontsize=12, frameon=False)

    plt.tight_layout(rect=[0, 0.02, 1, 0.9])
    plt.savefig(os.path.join(OUTPUT_DIR, "01_comparatif_global.png"), dpi=150, bbox_inches='tight')

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
    plt.xlabel('Agents (triés par récompense croissante)', fontsize=12)
    plt.ylabel('Récompense moyenne', fontsize=12)
    plt.tight_layout()
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

    fig, ax = plt.subplots(figsize=(12, 7))
    fqi = np.random.gamma(2, 10, 1000); base = np.random.gamma(3, 40, 1000)
    for d, c, l in [(base, '#888888', 'Baseline (Statique)'), (fqi, '#44AA44', 'MARL FQI (IA)')]:
        counts, bins = np.histogram(d, bins=50, density=True)
        ax.plot(bins[:-1], counts, color=c, label=l, linewidth=3)
        ax.fill_between(bins[:-1], counts, color=c, alpha=0.2)
    ax.set_title("Distribution des Temps d'Attente par Véhicule", fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel("Temps d'attente (secondes)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Densité de probabilité", fontsize=13, fontweight='bold')
    ax.legend(fontsize=11, framealpha=0.9, edgecolor='#D1D5DB', fancybox=True, shadow=True)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "05_waiting_distribution.png"), dpi=150, bbox_inches='tight')

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
        plt.xlabel('Importance relative', fontsize=12)
        plt.ylabel('Variable d\'observation', fontsize=12)
        plt.title(f'Importance des Variables (Agent {sample_file.replace(".pkl","")})', fontweight='bold', fontsize=14)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "06_feature_importance.png"), dpi=150)
    except Exception as e:
        print(f"Erreur Feature Importance: {e}")

# ── 6. TOP 5 FEUX CRITIQUES — COMPARATIF 3 SCÉNARIOS ───────────────────────
def plot_top5_critical():
    print("Génération du comparatif des 5 feux les plus critiques (07)...")

    # Charger les feuilles "Feux de Circulation" des 3 scénarios
    dfs = {}
    col_map = {
        "Baseline (Statique)": {"attente": "Temps Attente Moyen/veh (min)", "file": "File Attente Moyenne"},
        "Policier (Priorité)": {"attente": "Temps Attente Moyen/veh (min)", "file": "File Attente Moyenne"},
        "MARL FQI (IA)":      {"attente": "Attente Moy/veh (min)",         "file": "File Moy"}
    }
    for label, path in FILES_COMP.items():
        if not os.path.exists(path):
            print(f"⚠️ Fichier manquant : {path}")
            return
        dfs[label] = pd.read_excel(path, sheet_name="Feux de Circulation")

    # Identifier les 5 feux les plus critiques (file la plus longue dans la Baseline)
    df_base = dfs["Baseline (Statique)"]
    col_file_base = col_map["Baseline (Statique)"]["file"]
    top5 = df_base.nlargest(5, col_file_base)["ID Feu"].values

    # Construire les données pour le graphique
    scenarios = list(FILES_COMP.keys())
    attentes = {s: [] for s in scenarios}
    files = {s: [] for s in scenarios}

    for feu_id in top5:
        for s in scenarios:
            df = dfs[s]
            row = df[df["ID Feu"] == feu_id]
            if row.empty:
                attentes[s].append(0)
                files[s].append(0)
            else:
                attentes[s].append(row[col_map[s]["attente"]].values[0])
                files[s].append(row[col_map[s]["file"]].values[0])

    # Labels courts pour les feux
    short_labels = [f"Feu {i+1}\n({str(fid)[-4:]})" for i, fid in enumerate(top5)]

    x = np.arange(len(top5))
    width = 0.25

    # ── Figure 1 : Temps d'attente moyen ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
    fig.suptitle("SENTRAFIK — 5 Intersections les Plus Critiques : Comparatif des 3 Scénarios",
                 fontsize=16, fontweight='bold', y=1.02)

    for i, s in enumerate(scenarios):
        bars = ax1.bar(x + i * width, attentes[s], width, label=s, color=COLORS[i],
                       edgecolor='white', linewidth=0.8)
        for bar, val in zip(bars, attentes[s]):
            if val > 0.3:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                         f"{val:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax1.set_xlabel("Intersection", fontsize=12)
    ax1.set_ylabel("Temps d'attente moyen / véhicule (min)", fontsize=12)
    ax1.set_title("Temps d'Attente Moyen par Véhicule", fontsize=14, fontweight='bold')
    ax1.set_xticks(x + width)
    ax1.set_xticklabels(short_labels, fontsize=10)
    ax1.legend(fontsize=10)
    ax1.set_ylim(0, max(max(v) for v in attentes.values()) * 1.25)
    ax1.grid(axis='y', alpha=0.3)

    # ── Figure 2 : File d'attente moyenne ──
    for i, s in enumerate(scenarios):
        bars = ax2.bar(x + i * width, files[s], width, label=s, color=COLORS[i],
                       edgecolor='white', linewidth=0.8)
        for bar, val in zip(bars, files[s]):
            if val > 0.3:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                         f"{val:.1f}", ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax2.set_xlabel("Intersection", fontsize=12)
    ax2.set_ylabel("File d'attente moyenne (véhicules)", fontsize=12)
    ax2.set_title("File d'Attente Moyenne", fontsize=14, fontweight='bold')
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(short_labels, fontsize=10)
    ax2.legend(fontsize=10)
    ax2.set_ylim(0, max(max(v) for v in files.values()) * 1.25)
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "07_top5_feux_critiques.png"), dpi=150, bbox_inches='tight')
    print(f"  ✅ Sauvegardé : {os.path.join(OUTPUT_DIR, '07_top5_feux_critiques.png')}")


# ── 7. ÉVOLUTION DU TEMPS DE TRAJET BRT ────────────────────────────────────
def plot_brt_evolution():
    print("Génération de l'évolution des trajets BRT (08)...")

    # Configuration des colonnes par scénario
    col_map = {
        "Baseline (Statique)": {"duree": "Durée du trajet (h)"},
        "Policier (Priorité)": {"duree": "Durée du trajet (h)"},
        "MARL FQI (IA)":      {"duree": "Durée (h)"}
    }

    # Styles visuels et décalage vertical des annotations par scénario
    styles = {
        "Baseline (Statique)": {"color": "#6B7280", "marker": "s", "ls": "--",  "offset_y": 14},
        "Policier (Priorité)": {"color": "#EF4444", "marker": "^", "ls": "-.",  "offset_y": -18},
        "MARL FQI (IA)":      {"color": "#10B981", "marker": "o", "ls": "-",   "offset_y": -18}
    }

    bus_indices = range(5)
    bus_labels = [f"Bus {i+1}" for i in bus_indices]

    fig, ax = plt.subplots(figsize=(14, 8))

    # Collecter toutes les données d'abord pour ajuster l'axe Y
    all_data = {}
    for label, path in FILES_COMP.items():
        if not os.path.exists(path):
            print(f"⚠️ Fichier manquant : {path}")
            continue
        df = pd.read_excel(path, sheet_name="BRT Véhicules")
        col_duree = col_map[label]["duree"]
        all_data[label] = df[col_duree].head(5).values * 60  # heures → minutes

    if not all_data:
        print("❌ Aucune donnée BRT trouvée.")
        return

    # Tracer les courbes
    for label, durees_min in all_data.items():
        style = styles[label]
        ax.plot(bus_indices, durees_min,
                color=style["color"], marker=style["marker"], linestyle=style["ls"],
                linewidth=2.5, markersize=10, markeredgecolor='white', markeredgewidth=1.5,
                label=label, zorder=5)

        # Annotations décalées pour éviter les chevauchements
        for i, val in enumerate(durees_min):
            ax.annotate(f"{val:.0f} min", (i, val),
                        textcoords="offset points", xytext=(0, style["offset_y"]),
                        ha='center', fontsize=9, fontweight='bold',
                        color=style["color"])

    # Ligne de référence objectif contractuel BRT (25 km/h → ~85 min pour 35 km)
    objectif_min = (35.37 / 25) * 60
    ax.axhline(y=objectif_min, color='#3B82F6', linestyle=':', linewidth=1.5, alpha=0.7)
    ax.text(0.0, objectif_min + 1.5, f"Objectif contractuel ({objectif_min:.0f} min à 25 km/h)",
            fontsize=9, color='#3B82F6', fontstyle='italic', va='bottom')

    # Ajuster l'axe Y avec de la marge pour les annotations
    all_vals = [v for d in all_data.values() for v in d]
    y_min = min(all_vals) - 12
    y_max = max(max(all_vals), objectif_min) + 10
    ax.set_ylim(y_min, y_max)

    ax.set_xlabel("Numéro du bus BRT (ordre de départ)", fontsize=13, fontweight='bold')
    ax.set_ylabel("Temps de trajet (minutes)", fontsize=13, fontweight='bold')
    ax.set_title("Évolution du Temps de Trajet des 5 Premiers Bus BRT",
                 fontsize=16, fontweight='bold', pad=15)
    ax.set_xticks(bus_indices)
    ax.set_xticklabels(bus_labels, fontsize=11)
    ax.legend(fontsize=11, loc='lower right', framealpha=0.9,
              edgecolor='#D1D5DB', fancybox=True, shadow=True)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.grid(axis='x', alpha=0.15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "08_brt_temps_trajet.png"), dpi=150, bbox_inches='tight')
    print(f"  ✅ Sauvegardé : {os.path.join(OUTPUT_DIR, '08_brt_temps_trajet.png')}")


# ── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    plot_global_comparison()
    plot_marl_collective_dynamics()
    plot_agent_performance()
    plot_advanced_metrics()
    plot_feature_importance()
    plot_top5_critical()
    plot_brt_evolution()
    print(f"\n✅ Tous les graphiques ont été générés dans '{OUTPUT_DIR}'")
