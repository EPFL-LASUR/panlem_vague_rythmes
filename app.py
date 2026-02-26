import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from streamlit_folium import folium_static
import os
from PIL import Image
from scipy.stats import chi2_contingency
import textwrap
from streamlit.components.v1 import html
import streamlit.components.v1 as components

# === Import des fonctions et paramètres ===
from analysis_functions import (
    plot_global_distribution,
    plot_cross_distributions,
    plot_cross_distributions_grouped,
    plot_crosstab_likert_distribution,
    plot_likert_distribution,
    prepare_survey_data,
    perform_statistical_tests,
    analyse_croisee_questions,
    plot_croisement_questions,
    analyse_croisee_questions,
    plot_croisement_questions,
    process_multi_question_cross,
    plot_multi_cross_results,
    test_interaction_double_cross
)
from aesthetics import palette_dict, order_dict, var_labels
from questions_specs import questions_specs

# ===========================

# Mot de passe à définir
CORRECT_PASSWORD = "special_plr"

# Gestion de l'authentification
#if "authenticated" not in st.session_state:
    #st.session_state.authenticated = False

#if not st.session_state.authenticated:
    #st.title("Connexion")
    #password = st.text_input("Mot de passe", type="password")
    #if st.button("Se connecter"):
        #if password == CORRECT_PASSWORD:
            #st.session_state.authenticated = True
            #st.success("Authentification réussie!")
            #st.rerun()
        #else:
            #st.error("Mot de passe incorrect")
    #st.stop()  # Arrête l'exécution si non authentifié


# ===========================
# Charger le dataset
# ===========================
@st.cache_data
def load_data():
    return pd.read_csv("data_pour_app.csv")
plr = load_data()

# ===========================
# Titre principal
# ===========================
# Créer des onglets pour séparer les différentes fonctionnalités
main_tab1, main_tab2 = st.tabs(["Analyse par question", "Croisement de questions"])

# Définir weight_col par défaut avant toute utilisation
weight_col = None        

# ===========================
# Choix de la question
# ===========================
# Initialiser l'index de question dans session_state si nécessaire
with main_tab1:
    # Nettoyer les graphiques matplotlib
    plt.close('all')
    
    # Titre unique pour cet onglet
    st.title("Enquête mobilité et insécurité dans la ville nocturne")
    
    # Initialiser l'index de question dans session_state si nécessaire
    if "question_index" not in st.session_state:
        st.session_state.question_index = 0

    # Obtenir la liste des questions
    questions_list = list(questions_specs.keys())

    # Obtenir la question actuelle
    selected_question = questions_list[st.session_state.question_index]
    q_info = questions_specs[selected_question]
    current_index = st.session_state.question_index

    # Afficher un selectbox pour navigation directe
    selected_display = st.selectbox(
        "Choisir une question :", 
        [f"{q_id} - {questions_specs[q_id]['label']}" for q_id in questions_list],
        index=current_index
    )

    # Si changement via le selectbox, mettre à jour l'index
    selected_id = selected_display.split(" - ")[0]
    if selected_id != selected_question:
        st.session_state.question_index = questions_list.index(selected_id)
        selected_question = selected_id
        q_info = questions_specs[selected_question]
        current_index = st.session_state.question_index

    # ===========================
    # Sidebar pour filtres et options
    # ===========================
st.sidebar.header("⚙️ Options d'analyse")

# ===========================
# 1. PONDÉRATION (EN PREMIER)
# ===========================
st.sidebar.subheader("⚖️ Pondération")
weight_option = st.sidebar.radio(
    "Type de pondération :",
    ["Aucune pondération", "Pondération par canton"],
    help="Pondération cantonale = wgt_cant_trim_98",
)

# Définir weight_col globalement
weight_col = 'wgt_cant_trim_98' if weight_option == "Pondération par canton" else None

if weight_col:
    st.sidebar.info("✅ Analyses pondérées avec les poids cantonaux")

# ===========================
# 2. VARIABLES À CROISER
# ===========================
# Variables contextuelles disponibles avec leurs labels d'affichage
context_vars_labels = {
    "cat_domicile": "Typologie du lieu de domicile",
    "genre": "Genre",
    "formation": "Formation",
    "revenu": "Revenu",
    "age": "Âge",
    "type_menage": "Composition du ménage"
}

all_context_vars = list(context_vars_labels.keys())

# Premier niveau de croisement
selected_vars = st.sidebar.multiselect(
    "Variables à croiser (niveau 1)",
    options=all_context_vars,
    default=["genre"],
    format_func=lambda x: context_vars_labels[x],
    help="Sélectionnez les variables principales à analyser"
)

# Second niveau de croisement (optionnel)
enable_double_cross = st.sidebar.checkbox(
    "🔀 Activer un second niveau de croisement",
    value=False,
    help="Exemple : analyser par Genre (niveau 1) puis par Âge (niveau 2)"
)

selected_vars_level2 = []
if enable_double_cross and selected_vars:
    # Exclure les variables déjà sélectionnées au niveau 1
    remaining_vars = [v for v in all_context_vars if v not in selected_vars]
    
    if remaining_vars:
        selected_vars_level2 = st.sidebar.multiselect(
            "Variables à croiser (niveau 2)",
            options=remaining_vars,
            default=["age"] if "age" in remaining_vars else [],
            format_func=lambda x: context_vars_labels[x],
            help="Ces variables seront analysées DANS chaque catégorie du niveau 1"
        )
        
        if selected_vars_level2:
            st.sidebar.success(f"✅ Double croisement actif : {context_vars_labels[selected_vars[0]]} → {context_vars_labels[selected_vars_level2[0]]}")
    else:
        st.sidebar.warning("⚠️ Toutes les variables sont déjà sélectionnées au niveau 1")

# ===========================
# 3. AFFICHAGE CARACTÉRISTIQUES ÉCHANTILLON
# ===========================
# Si "Aucune pondération" est sélectionné
if weight_option == "Aucune pondération":
    # Ajouter une expansion pour les caractéristiques de l'échantillon
    with st.expander("📊 Voir les caractéristiques de l'échantillon"):
        # Calculer les distributions avec les dictionnaires existants
        distributions = {
            "Typologie du domicile": {
                "data": plr['cat_domicile'].value_counts(normalize=True) * 100,
                "palette": palette_dict["cat_domicile"],
                "order": order_dict["cat_domicile"]
            },
            "Genre": {
                "data": plr['genre'].value_counts(normalize=True) * 100,
                "palette": palette_dict["genre"],
                "order": order_dict["genre"]
            },
            "Âge": {
                "data": plr['age'].value_counts(normalize=True) * 100,
                "palette": palette_dict["age"],
                "order": order_dict["age"]
            },
            "Formation": {
                "data": plr['formation'].value_counts(normalize=True) * 100,
                "palette": palette_dict["formation"],
                "order": order_dict["formation"]
            },
            "Revenu": {
                "data": plr['revenu'].value_counts(normalize=True) * 100,
                "palette": palette_dict["revenu"],
                "order": order_dict["revenu"]
            },
            "Type de ménage": {
                "data": plr['type_menage'].value_counts(normalize=True) * 100,
                "palette": palette_dict["type_menage"],
                "order": order_dict["type_menage"]
            }
        }

        # Créer un sélecteur pour choisir la caractéristique à afficher
        selected_dist = st.selectbox(
            "Choisir une caractéristique à visualiser :",
            list(distributions.keys())
        )

        # Afficher le graphique sélectionné (barres)
        fig, ax = plt.subplots(figsize=(10, 6))

        data = distributions[selected_dist]["data"]
        palette = distributions[selected_dist]["palette"]
        order = distributions[selected_dist]["order"]

        # Réindexer si un ordre est fourni, sinon trier par fréquence
        if order is not None:
            data = data.reindex(order).dropna()
        else:
            data = data.sort_values(ascending=False)

        # Libellés compactés et couleurs correspondant aux catégories
        labels = [textwrap.fill(str(l), width=12) for l in data.index]
        if isinstance(palette, dict):
            colors = [palette.get(k, "#333333") for k in data.index]
        else:
            colors = [palette[i % len(palette)] for i in range(len(data))]

        ax.bar(labels, data.values, color=colors)
        ax.set_title(f"Répartition {selected_dist.lower()} dans l'échantillon", fontsize=15, weight="bold")
        ax.set_xlabel(selected_dist)
        ax.set_ylabel("Pourcentage (%)")
        ax.set_ylim(0, 100)

        # Étiquettes de pourcentage
        for container in ax.containers:
            ax.bar_label(container, fmt="%.1f%%")

        sns.despine()
        plt.tight_layout()
        st.pyplot(fig)

# ===========================
# 4. NORMALISATION
# ===========================
st.sidebar.subheader("Normalisation")
cross_analysis_type = st.sidebar.radio(
    "Type d'analyse croisée :",
    ["Standard", "Groupée (100% par modalité)"],
    help="Standard = 100% par graphique\nGroupée = 100% par modalité",
    key="normalisation_type"
)

# ===========================
# 5. TESTS STATISTIQUES
# ===========================
st.sidebar.subheader("Tests statistiques")
show_stats = st.sidebar.multiselect(
    "Type(s) d'analyse statistique :",
    options=["Test du chi-2", "Résidus standardisés", "V de Cramer"],
    help="Chi-2 = Test d'indépendance\nRésidus = Force et direction des associations\nV de Cramer = Force des relations",
    key="stats_type"
)

# ===========================
# 6. FILTRES GÉOGRAPHIQUES
# ===========================
st.sidebar.subheader("📍 Filtre géographique (optionnel)")

filtre_actif = False

possible_local_cols = [
    "Localité_actuel", "AGGLO_CH_dom"
]
found_local_col = next((c for c in possible_local_cols if c in plr.columns), None)

if found_local_col:
    communes_disponibles = sorted(plr[found_local_col].dropna().unique().tolist())
    
    if communes_disponibles:
        selected_commune = st.sidebar.selectbox(
            "Filtrer par agglo :",
            options=["Toutes"] + communes_disponibles,
            help="Affinez par commune"
        )
    else:
        st.sidebar.info("Aucune commune disponible")
        selected_commune = "Toutes"
    
    if selected_commune != "Toutes":
        plr = plr[plr[found_local_col] == selected_commune]
        st.sidebar.success(f"✅ Filtre actif : {len(plr)} répondants de {selected_commune}")
        filtre_actif = True
else:
    st.sidebar.info("ℹ️ Le filtre par commune n'est pas disponible")
# ===========================
# Retour dans main_tab1 pour les analyses
# ===========================
with main_tab1:
    # ===========================
    # Cas 1 : Questions simples (single)
    # ===========================
    if q_info["type"] == "single":
        st.subheader("Distribution globale")
        
        # Distribution globale
        plot_global_distribution(
            df=plr.dropna(subset=[selected_question]),
            question=selected_question,
            question_label=q_info["label"],
            order=order_dict.get(selected_question),
            palette=palette_dict.get(selected_question, "black"),
            weight=weight_col
        )
        st.pyplot(plt.gcf())
        
        # Analyse croisée NORMALE (créer figures d'abord)
        if selected_vars:
            st.subheader(f"Analyse croisée par variables sociodémographiques - {q_info['label']}")
            
            if cross_analysis_type == "Standard":
                figures, _ = plot_cross_distributions(
                    df=plr.dropna(subset=[selected_question]),
                    question=selected_question,
                    question_label=q_info["label"],
                    colonnes_croisables=selected_vars,
                    palette_dict=palette_dict,
                    order_dict=order_dict,
                    var_labels=var_labels,
                    weight=weight_col
                )
            else:  # Groupée
                figures = plot_cross_distributions_grouped(
                    df=plr.dropna(subset=[selected_question]),
                    question=selected_question,
                    question_label=q_info["label"],
                    colonnes_croisables=selected_vars,
                    palette_dict=palette_dict,
                    order_dict=order_dict,
                    var_labels=var_labels,
                    weight=weight_col
                )
            
            # Afficher les figures du niveau 1
            for fig in figures.values():
                st.pyplot(fig)
        
        # Double croisement si activé
        if enable_double_cross and selected_vars_level2:
            st.subheader("🔀 Analyse à double croisement")
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    st.markdown(f"### {context_vars_labels[var1]} → {context_vars_labels[var2]}")
                    
                    # Obtenir les catégories de niveau 1
                    if var1 in order_dict and order_dict[var1] is not None:
                        level1_cats = [cat for cat in order_dict[var1] if cat in plr[var1].unique()]
                    else:
                        level1_cats = sorted(plr[var1].dropna().unique())
                    
                    # Créer des onglets pour chaque catégorie de niveau 1
                    tabs = st.tabs([f"{cat}" for cat in level1_cats])
                    
                    for tab, cat1 in zip(tabs, level1_cats):
                        with tab:
                            # Filtrer les données pour cette catégorie
                            plr_filtered = plr[plr[var1] == cat1].copy()
                            
                            st.info(f"📊 {len(plr_filtered)} répondants ({cat1})")
                            
                            # Générer le graphique croisé pour le niveau 2
                            if cross_analysis_type == "Standard":
                                figures_double, _ = plot_cross_distributions(
                                    df=plr_filtered.dropna(subset=[selected_question]),
                                    question=selected_question,
                                    question_label=f"{q_info['label']} ({cat1})",
                                    colonnes_croisables=[var2],
                                    palette_dict=palette_dict,
                                    order_dict=order_dict,
                                    var_labels=var_labels,
                                    weight=weight_col
                                )
                            else:  # Groupée
                                figures_double = plot_cross_distributions_grouped(
                                    df=plr_filtered.dropna(subset=[selected_question]),
                                    question=selected_question,
                                    question_label=f"{q_info['label']} ({cat1})",
                                    colonnes_croisables=[var2],
                                    palette_dict=palette_dict,
                                    order_dict=order_dict,
                                    var_labels=var_labels,
                                    weight=weight_col
                                )
                            
                            # Afficher les graphiques
                            for fig in figures_double.values():
                                st.pyplot(fig)
        
        # Tests statistiques
        if selected_vars and show_stats:
            st.subheader("Tests statistiques")
            for var in selected_vars:
                if var in plr.columns:
                    if "Test du chi-2" in show_stats or "Résidus standardisés" in show_stats:
                        for test_type in show_stats:
                            if test_type in ["Test du chi-2", "Résidus standardisés"]:
                                perform_statistical_tests(
                                    df=plr,
                                    question=selected_question,
                                    var=var,
                                    var_labels=var_labels,
                                    weight_col=weight_col,
                                    test_type=test_type
                                )

        # TESTS D'INTERACTION pour le double croisement
        if enable_double_cross and selected_vars_level2 and show_stats:
            st.subheader("🔬 Tests statistiques d'interaction")
            
            st.info("""
            Ces tests permettent de savoir si l'effet d'une variable (ex: Genre) **varie** 
            selon une autre variable (ex: Âge).
            """)
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    test_interaction_double_cross(
                        df=plr.dropna(subset=[selected_question, var1, var2]),
                        question=selected_question,
                        var1=var1,
                        var2=var2,
                        var_labels=context_vars_labels,
                        weight_col=weight_col,
                    )
   # ===========================
    # CAS 2 : Questions multi-réponses
    # ===========================
    elif q_info["type"] == "multi":
        st.subheader("Répartition des réponses multiples")

        # Utiliser prepare_survey_data pour traiter la question multi-réponses
        prepared_data = prepare_survey_data(
            df=plr,
            question_specs={selected_question: q_info},
            context_vars=selected_vars,
            weight=weight_col
        )
        
        # Récupérer les données préparées pour cette question
        df_prepared = prepared_data[selected_question]
        
        # Déterminer l'ordre basé sur les fréquences de la distribution globale
        global_counts = df_prepared["reason_label"].value_counts(normalize=True)
        fixed_order = global_counts.index.tolist()
        
        # Distribution globale avec l'ordre déterminé
        plot_global_distribution(
            df=df_prepared,
            question="reason_label",
            question_label=q_info["label"],
            order=fixed_order,
            weight=weight_col
        )
        st.pyplot(plt.gcf())

        # ===========================
        # ANALYSE CROISÉE NIVEAU 1
        # ===========================
        if selected_vars:
            st.subheader(f"Analyse croisée par variables sociodémographiques - {q_info['label']}")
            
            if cross_analysis_type == "Standard":
                figures, _ = plot_cross_distributions(
                    df=df_prepared,
                    question="reason_label",
                    question_label=q_info["label"],
                    colonnes_croisables=selected_vars,
                    palette_dict=palette_dict,
                    order_dict={"reason_label": fixed_order},
                    var_labels=var_labels,
                    weight=weight_col
                )
            else:  # Groupée
                figures = plot_cross_distributions_grouped(
                    df=df_prepared,
                    question="reason_label",
                    question_label=q_info["label"],
                    colonnes_croisables=selected_vars,
                    palette_dict=palette_dict,
                    order_dict={"reason_label": fixed_order},
                    var_labels=var_labels,
                    weight=weight_col,
                )

            # Afficher les figures du niveau 1
            for fig in figures.values():
                st.pyplot(fig)
        
        # ===========================
        # DOUBLE CROISEMENT (NIVEAU 2)
        # ===========================
        if enable_double_cross and selected_vars_level2:
            st.subheader("🔀 Analyse à double croisement")
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    st.markdown(f"### {context_vars_labels[var1]} → {context_vars_labels[var2]}")
                    
                    # Obtenir les catégories de niveau 1 depuis PLR (pas df_prepared)
                    if var1 in order_dict and order_dict[var1] is not None:
                        level1_cats = [cat for cat in order_dict[var1] if cat in plr[var1].unique()]
                    else:
                        level1_cats = sorted(plr[var1].dropna().unique())
                    
                    # Créer des onglets pour chaque catégorie de niveau 1
                    tabs = st.tabs([f"{cat}" for cat in level1_cats])
                    
                    for tab, cat1 in zip(tabs, level1_cats):
                        with tab:
                            # Filtrer PLR AVANT prepare_survey_data
                            plr_filtered = plr[plr[var1] == cat1].copy()
                            
                            st.info(f"📊 {len(plr_filtered)} répondants ({cat1})")
                            
                            # Préparer les données multi pour ce sous-groupe
                            prepared_data_filtered = prepare_survey_data(
                                df=plr_filtered,
                                question_specs={selected_question: q_info},
                                context_vars=[var2],  # var2 doit être inclus ici
                                weight=weight_col
                            )
                            
                            df_filtered_prepared = prepared_data_filtered[selected_question]
                            
                            # Vérifier que var2 est présent
                            if var2 not in df_filtered_prepared.columns:
                                st.error(f"❌ La variable '{var2}' n'est pas disponible dans les données")
                                continue
                            
                            # Vérifier qu'il y a des données
                            if df_filtered_prepared.empty:
                                st.warning(f"⚠️ Aucune donnée pour {cat1}")
                                continue
                            
                            # Générer le graphique croisé pour le niveau 2
                            try:
                                if cross_analysis_type == "Standard":
                                    figures_double, _ = plot_cross_distributions(
                                        df=df_filtered_prepared,
                                        question="reason_label",
                                        question_label=f"{q_info['label']} ({cat1})",
                                        colonnes_croisables=[var2],
                                        palette_dict=palette_dict,
                                        order_dict={"reason_label": fixed_order},
                                        var_labels=var_labels,
                                        weight=weight_col
                                    )
                                else:  # Groupée
                                    figures_double = plot_cross_distributions_grouped(
                                        df=df_filtered_prepared,
                                        question="reason_label",
                                        question_label=f"{q_info['label']} ({cat1})",
                                        colonnes_croisables=[var2],
                                        palette_dict=palette_dict,
                                        order_dict={"reason_label": fixed_order},
                                        var_labels=var_labels,
                                        weight=weight_col
                                    )
                                
                                # Afficher les graphiques
                                for fig in figures_double.values():
                                    st.pyplot(fig)
                                    
                            except KeyError as e:
                                st.error(f"❌ Erreur lors du croisement : {str(e)}")
                                st.info(f"💡 Variables disponibles : {df_filtered_prepared.columns.tolist()}")
                            except Exception as e:
                                st.error(f"❌ Erreur inattendue : {str(e)}")

        # ===========================
        # TESTS STATISTIQUES
        # ===========================
        if selected_vars and show_stats:
            st.subheader("Tests statistiques")
            selected_cols = list(q_info["labels"].keys())
            for var in selected_vars:
                if var in plr.columns:
                    st.markdown(f"### Tests pour {var_labels.get(var, var)}")
                    for col in selected_cols:
                        st.markdown(f"#### {q_info['labels'][col]}")
                        for test_type in show_stats:
                            perform_statistical_tests(
                                df=plr,
                                question=col,
                                var=var,
                                var_labels=var_labels,
                                weight_col=weight_col,
                                test_type=test_type
                            )

        # TESTS D'INTERACTION pour le double croisement
        if enable_double_cross and selected_vars_level2 and show_stats:
            st.subheader("🔬 Tests statistiques d'interaction (questions multi-réponses)")
            
            st.info("""
            Ces tests analysent si l'effet d'une variable varie selon une autre pour chaque sous-question.
            """)
            
            # Pour chaque sous-question de la question multi
            selected_cols = list(q_info["labels"].keys())
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    st.markdown(f"### {context_vars_labels[var1]} × {context_vars_labels[var2]}")
                    
                    # Test pour chaque sous-question
                    for col in selected_cols:
                        st.markdown(f"#### Sous-question : {q_info['labels'][col]}")
                        
                        test_interaction_double_cross(
                            df=plr.dropna(subset=[col, var1, var2]),
                            question=col,
                            var1=var1,
                            var2=var2,
                            var_labels=context_vars_labels,
                            weight_col=weight_col
                        )
    # ===========================
    # CAS 3bis : Questions 20 avec images
    # ===========================
    # Définir le chemin de base (au début du fichier, après les imports)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    if selected_question in ["P2_Q20a", "P2_Q20b", "P2_Q20c", "P2_Q20d", "P2_Q20e", "P2_Q20f"]:
        
        # Construction manuelle de l'ordre des colonnes (1, 2, 3)
        selected_cols = []
        for i in range(1, 4):  # Pour les questions 1, 2, 3
            col_name = f"{selected_question}_{i}"
            if col_name in q_info["labels"]:
                selected_cols.append(col_name)

        # Créer un dictionnaire pour l'ordre des items
        item_order = {col: i for i, col in enumerate(selected_cols)}

        image_paths = {
            "P2_Q20a": os.path.join(BASE_DIR, "selection-image", "image_1.jpg"),
            "P2_Q20b": os.path.join(BASE_DIR, "selection-image", "image_2.jpg"),
            "P2_Q20c": os.path.join(BASE_DIR, "selection-image", "image_3.jpg"),
            "P2_Q20d": os.path.join(BASE_DIR, "selection-image", "image_4.jpg"),
            "P2_Q20e": os.path.join(BASE_DIR, "selection-image", "image_5.jpg"),
            "P2_Q20f": os.path.join(BASE_DIR, "selection-image", "image_6.jpg")
        }

        try:
            st.subheader("📸 Image de référence")
            image_path = image_paths[selected_question]

            if os.path.exists(image_path):
                image = Image.open(image_path)
                st.image(
                    image,
                    caption=q_info["label"],
                    use_container_width=True
                )

                st.subheader(f"Distribution globale - {q_info['label']}")

                # Préparation des données Likert en format long
                if weight_col:
                    df_long = plr[selected_cols + [weight_col]].melt(
                        id_vars=[weight_col],
                        value_vars=selected_cols,
                        var_name="item",
                        value_name="score"
                    )
                else:
                    df_long = plr[selected_cols].melt(
                        var_name="item",
                        value_name="score"
                    )

                # Ajouter l'ordre et les labels
                df_long["item_order"] = df_long["item"].map(item_order)
                df_long["item_label"] = df_long["item"].map(q_info["labels"])
                
                # Trier selon l'ordre défini
                df_long = df_long.sort_values("item_order")

                # Mapping texte → score
                score_mapping = {v: k for k, v in q_info["scale_labels"].items()}
                df_long["score_num"] = df_long["score"].map(score_mapping)
                df_long = df_long.dropna()

                # Graphique global (sans inversion car toutes les sous-questions ensemble)
                plot_likert_distribution(
                    df=df_long,
                    item_col="item_label",
                    score_col="score_num",
                    score_labels=q_info.get("scale_labels"),
                    title="Réponses",
                    weight=weight_col,
                    inverse_colors=False
                )
                st.pyplot(plt.gcf())

                # Copier plr pour analyse croisée
                plr_for_analysis = plr.copy()
                
                # Mapping aussi dans plr pour analyse croisée
                for col in selected_cols:
                    if col in plr_for_analysis.columns:
                        plr_for_analysis[col] = plr_for_analysis[col].map(score_mapping)
                        if plr_for_analysis[col].dropna().empty:
                            st.warning(f"La colonne {col} ne contient aucune réponse valide après mapping.")

                # Créer le dictionnaire des libellés de questions
                question_labels = {col: q_info["labels"][col] for col in selected_cols}

                # Analyse croisée
                if selected_vars:
                    st.subheader(f"Analyse croisée par variables sociodémographiques - {q_info['label']}")
                    for var in selected_vars:
                        if var in plr_for_analysis.columns:
                            st.markdown(f"### {var_labels.get(var, var)}")
                            
                            # Inverser pour les colonnes se terminant par _1 et _2
                            inverse_dict = {}
                            for col in selected_cols:
                                # Extraire le numéro à la fin (ex: P2_Q20c_1 → "1")
                                suffix = col.split('_')[-1]
                                # Inverser si c'est _1 ou _2
                                inverse_dict[col] = (suffix in ['1', '2'])
                            
                            figures = plot_crosstab_likert_distribution(
                                df=plr_for_analysis,
                                questions=selected_cols,
                                context_vars=[var],
                                question_specs=questions_specs,
                                question_labels=question_labels,
                                palette_dict=palette_dict,
                                order_dict=order_dict,
                                var_labels=var_labels,
                                score_labels=q_info.get("scale_labels"),
                                score_order=sorted(q_info.get("scale_labels", {}).keys()),
                                weight=weight_col,
                                normalize="demographic" if cross_analysis_type == "Groupée (100% par modalité)" else "group",
                                inverse_colors_dict=inverse_dict  # Inversion pour _1 et _2
                            )
                            for fig in figures.values():
                                st.pyplot(fig)
                        else:
                            st.warning(f"La variable **{var}** n'existe pas dans le dataset.")

                # Tests statistiques pour questions Likert
                if selected_vars and show_stats:
                    st.subheader("Tests statistiques")
                    selected_cols = list(q_info["labels"].keys())
                    for var in selected_vars:
                        if var in plr.columns:
                            st.markdown(f"### Tests pour {var_labels.get(var, var)}")
                            for col in selected_cols:
                                st.markdown(f"#### {q_info['labels'][col]}")
                                for test_type in show_stats:  # Boucle sur chaque test sélectionné
                                    perform_statistical_tests(
                                        df=plr,
                                        question=col,
                                        var=var,
                                        var_labels=var_labels,
                                        weight_col=weight_col,
                                        test_type=test_type  # Passer le type de test actuel
                                    )
            else:
                st.error(f"Image non trouvée : {image_path}")
        except Exception as e:
            st.error(f"Une erreur est survenue lors de l'affichage de l'image ou du graphique : {e}")

# Ligne 676-754 : Remplacer tout le CAS 3 par :

    # ===========================
    # Cas 3 : Questions Likert (avec sous-questions)
    # ===========================   
    elif q_info["type"] == "likert":
        st.subheader("Distribution globale (Likert)")

        # Colonnes de la question
        selected_cols = list(q_info["labels"].keys())

        # Préparation des données au format long
        if weight_col:
            df_long = plr[selected_cols + [weight_col]].melt(
                id_vars=[weight_col],
                value_vars=selected_cols,
                var_name="item",
                value_name="score"
            )
        else:
            df_long = plr[selected_cols].melt(
                var_name="item",
                value_name="score"
            )
        df_long["item_label"] = df_long["item"].map(q_info["labels"])

        # Conversion des scores
        score_mapping = {v: k for k, v in q_info["scale_labels"].items()}
        df_long["score_num"] = df_long["score"].map(score_mapping)
        df_long = df_long.dropna()

        # Graphique global
        plot_likert_distribution(
            df=df_long,
            item_col="item_label",
            score_col="score_num",
            score_labels=q_info.get("scale_labels"),
            title="Réponses",
            weight=weight_col
        )
        st.pyplot(plt.gcf())
        
        # Conversion des réponses texte en scores numériques pour plr
        for col in selected_cols:
            if col in plr.columns:
                plr[col] = plr[col].map(score_mapping)
        
        # Analyse croisée NORMALE (niveau 1)
        if selected_vars:
            st.subheader(f"Analyse croisée par variables sociodémographiques - {q_info['label']}")
            
            normalize_mode = "demographic" if cross_analysis_type == "Groupée (100% par modalité)" else "group"
            
            for var in selected_vars:
                if var in plr.columns:
                    st.markdown(f"### {var_labels.get(var, var)}")

                    figures = plot_crosstab_likert_distribution(
                        df=plr,
                        questions=selected_cols,
                        context_vars=[var],
                        question_specs=questions_specs,
                        question_labels=q_info["labels"],
                        palette_dict=palette_dict,
                        order_dict=order_dict,
                        var_labels=var_labels,
                        score_labels=q_info.get("scale_labels"),
                        score_order=[1, 2, 3, 4, 5],
                        weight=weight_col,
                        normalize=normalize_mode
                    )
                    for fig in figures.values():
                        st.pyplot(fig)
        
        # Double croisement si activé
        if enable_double_cross and selected_vars_level2:
            st.subheader("🔀 Analyse à double croisement")
            
            normalize_mode = "demographic" if cross_analysis_type == "Groupée (100% par modalité)" else "group"
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    st.markdown(f"### {context_vars_labels[var1]} → {context_vars_labels[var2]}")
                    
                    # Obtenir les catégories de niveau 1
                    if var1 in order_dict and order_dict[var1] is not None:
                        level1_cats = [cat for cat in order_dict[var1] if cat in plr[var1].unique()]
                    else:
                        level1_cats = sorted(plr[var1].dropna().unique())
                    
                    # Créer des onglets pour chaque catégorie de niveau 1
                    tabs = st.tabs([f"{cat}" for cat in level1_cats])
                    
                    for tab, cat1 in zip(tabs, level1_cats):
                        with tab:
                            # Filtrer les données pour cette catégorie
                            plr_filtered = plr[plr[var1] == cat1].copy()
                            
                            st.info(f"📊 {len(plr_filtered)} répondants ({cat1})")
                            
                            # Générer le graphique Likert croisé pour le niveau 2
                            figures_double = plot_crosstab_likert_distribution(
                                df=plr_filtered,
                                questions=selected_cols,
                                context_vars=[var2],
                                question_specs=questions_specs,
                                question_labels=q_info["labels"],
                                palette_dict=palette_dict,
                                order_dict=order_dict,
                                var_labels=var_labels,
                                score_labels=q_info.get("scale_labels"),
                                score_order=[1, 2, 3, 4, 5],
                                weight=weight_col,
                                normalize=normalize_mode
                            )
                            
                            # Afficher les graphiques
                            for fig in figures_double.values():
                                st.pyplot(fig)

        # Tests statistiques pour questions Likert
        if selected_vars and show_stats:
            st.subheader("Tests statistiques")
            selected_cols = list(q_info["labels"].keys())
            for var in selected_vars:
                if var in plr.columns:
                    st.markdown(f"### Tests pour {var_labels.get(var, var)}")
                    for col in selected_cols:
                        st.markdown(f"#### {q_info['labels'][col]}")
                        for test_type in show_stats:
                            perform_statistical_tests(
                                df=plr,
                                question=col,
                                var=var,
                                var_labels=var_labels,
                                weight_col=weight_col,
                                test_type=test_type
                            )

        # TESTS D'INTERACTION pour le double croisement
        if enable_double_cross and selected_vars_level2 and show_stats:
            st.subheader("🔬 Tests statistiques d'interaction (échelle Likert)")
            
            st.info("""
            Ces tests analysent si l'effet d'une variable varie selon une autre pour chaque item Likert.
            """)
            
            # Pour chaque item de l'échelle Likert
            selected_cols = list(q_info["labels"].keys())
            
            for var1 in selected_vars:
                for var2 in selected_vars_level2:
                    st.markdown(f"### {context_vars_labels[var1]} × {context_vars_labels[var2]}")
                    
                    # Test pour chaque item Likert
                    for col in selected_cols:
                        st.markdown(f"#### Item : {q_info['labels'][col]}")
                        
                        test_interaction_double_cross(
                            df=plr.dropna(subset=[col, var1, var2]),
                            question=col,
                            var1=var1,
                            var2=var2,
                            var_labels=context_vars_labels,
                            weight_col=weight_col,
                        )


    # =============================
    # CAS 4 : Point avec hexagones H3 améliorés
    # =============================

    elif selected_question in ["P2_Q12a", "P2_Q13a"]:
        st.subheader("🗺️ Cartographie des endroits")
        
        # Chargement des données GPS
        @st.cache_data
        def load_gps_data():
            return pd.read_csv("endroits_kepler.csv")
        
        def validate_gps_df(df, required=("lat", "lon")):
            """Valide et nettoie les coordonnées GPS"""
            for col in required:
                if col not in df.columns:
                    raise ValueError(f"Colonne manquante : {col}")
            df = df.dropna(subset=list(required))
            df = df[(df["lat"].between(-90, 90)) & (df["lon"].between(-180, 180))]
            return df
        
        def compute_hex_stats(df, h3_module, res=9):
            """Calcule les statistiques par hexagone H3"""
            df["h3_hex"] = df.apply(
                lambda r: h3_module.latlng_to_cell(r["lat"], r["lon"], res), axis=1
            )
            hex_stats = df.groupby("h3_hex").agg({
                'type_lieu': [
                    lambda x: (x == "Endroit insécurisant").sum() / len(x) * 100 if len(x) > 0 else 0,
                    'count'
                ]
            }).reset_index()
            hex_stats.columns = ['h3_hex', 'insecurity_score', 'point_count']
            
            # Calcul de l'opacité amélioré
            def calculate_enhanced_opacity(count):
                if pd.isna(count) or count == 0:
                    return 0.10
                elif count == 1:
                    return 0.12
                elif count == 2:
                    return 0.22
                elif count == 3:
                    return 0.35
                elif count == 4:
                    return 0.50
                elif count == 5:
                    return 0.60
                elif count == 6:
                    return 0.70
                elif count <= 10:
                    return 0.75 + (count - 6) * 0.02
                else:
                    return min(0.85 + (count - 10) * 0.01, 0.95)
            
            hex_stats['opacity'] = hex_stats['point_count'].apply(calculate_enhanced_opacity)
            return hex_stats
        
        def apply_zone_filter(hex_stats, zone_filter, min_opacity=0.69):
            """Applique le filtre de zone de sécurité"""
            if zone_filter == "Zones insécures (>80%)":
                hex_stats = hex_stats[hex_stats["insecurity_score"] > 80]
                # Filtrer les hexagones avec opacité trop faible
                hex_stats = hex_stats[hex_stats["opacity"] >= min_opacity]
            elif zone_filter == "Zones sûres (<20%)":
                hex_stats = hex_stats[hex_stats["insecurity_score"] < 20]
                # Filtrer les hexagones avec opacité trop faible
                hex_stats = hex_stats[hex_stats["opacity"] >= min_opacity]
            # Si "Tous", ne pas appliquer de filtre (ni sur le score ni sur l'opacité)
            return hex_stats
        
        df_gps = load_gps_data()
        
        # Filtres dans des colonnes
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sentiment = st.radio(
                "Afficher les endroits :",
                ["Tous", "Endroit insécurisant", "Endroit sécurisant"]
            )
        
        with col2:
            zone_filter = st.radio(
                "Filtrer par zone (sécurité) :",
                ["Tous", "Zones insécures (>80%)", "Zones sûres (<20%)"],
                help="Filtre basé sur le score d'insécurité des hexagones"
            )
        
        with col3:
            genre_filter = st.radio(
                "Filtrer par genre :",
                ["Tous", "Femmes", "Hommes"]
            )
        
        with col4:
            show_comments = st.checkbox("Afficher les commentaires", value=False)
        
        # Options hexagones H3 (nouvelle ligne)
        col5, col6 = st.columns(2)
        
        with col5:
            show_hexagons = st.checkbox("Visualisation par hexagones H3", value=True)
        
        with col6:
            if show_hexagons:
                h3_resolution = st.slider(
                    "Résolution H3 (taille hexagones)",
                    min_value=7,
                    max_value=11,
                    value=9,
                    help="Plus la résolution est élevée, plus les hexagones sont petits.\n"
                        "7 = ~5.2 km², 8 = ~0.74 km² (499 m de côté), 9 = ~0.10 km² (174 m de côté), 10 = ~0.015 km² (87m de côté), 11 = ~0.002 km²"
                )
            else:
                h3_resolution = 9  # valeur par défaut
        
        # Filtrage des données
        df_map = df_gps.copy()
        
        # Filtre par sentiment
        if sentiment != "Tous":
            df_map = df_map[df_map["type_lieu"] == sentiment]
            
        # Filtre par genre
        if genre_filter != "Tous":
            if genre_filter == "Femmes":
                df_map = df_map[df_map["genre"] == "Femme"]
            else:
                df_map = df_map[df_map["genre"] == "Homme"]

        # === VISUALISATION PAR HEXAGONES H3 ===
        if show_hexagons:
            try:
                import h3
                import numpy as np
                
                st.subheader("Carte interactive par hexagones H3")
                
                # Afficher info sur la taille des hexagones
                hex_sizes = {
                    7: "~5.2 km² (~2.5 km de côté)",
                    8: "~0.74 km² (~940 m de côté)",
                    9: "~0.10 km² (~350 m de côté)",
                    10: "~0.015 km² (~130 m de côté)",
                    11: "~0.002 km² (~50 m de côté)"
                }
                st.info(f"ℹ️ Taille approximative des hexagones : **{hex_sizes.get(h3_resolution, 'inconnue')}**")
                
                # Vérifier que nous avons des données
                if df_map.empty:
                    st.warning("Aucune donnée à afficher avec les filtres sélectionnés")
                else:
                    # Validation et nettoyage des coordonnées
                    df_map = validate_gps_df(df_map, required=("lat", "lon"))
                    
                    # Calcul des statistiques par hexagone avec résolution dynamique
                    hex_stats = compute_hex_stats(df_map, h3, res=h3_resolution)
                    
                    # Appliquer le filtre de zone
                    hex_stats = apply_zone_filter(hex_stats, zone_filter, min_opacity=0.69)
                    
                    if hex_stats.empty:
                        st.warning("Aucun hexagone ne correspond aux filtres sélectionnés.")
                    else:
                        # Limite d'affichage pour éviter de surcharger la carte
                        MAX_HEX = 2500
                        if len(hex_stats) > MAX_HEX:
                            st.info(f"Trop d'hexagones ({len(hex_stats)}) — limitation à {MAX_HEX} pour performance.")
                            hex_stats = hex_stats.nlargest(MAX_HEX, "point_count")
                        
                        # Création de la carte (centrage dynamique)
                        center_lat = float(df_map["lat"].median())
                        center_lon = float(df_map["lon"].median())
                        # Coordonnées de la Place de la Riponne à Lausanne
                        RIPONNE_LAT = 46.5225
                        RIPONNE_LON = 6.6328
                        
                        m = folium.Map(
                            location=[RIPONNE_LAT, RIPONNE_LON], 
                            zoom_start=14,
                            tiles='OpenStreetMap'
                        )
                        # Colormap pour le score d'insécurité
                        colormap = folium.LinearColormap(
                            colors=["#0ea74e", "#f1a20f", "#bc200e"],
                            vmin=0, 
                            vmax=100,
                            caption="Score d'insécurité (%)"
                        )

                        # Ajouter les hexagones à la carte
                        hexagones_ajoutes = 0
                        for _, row in hex_stats.iterrows():
                            try:
                                # Obtenir les coordonnées de l'hexagone
                                boundary = h3.cell_to_boundary(row["h3_hex"])
                                
                                # Couleur basée sur le score d'insécurité
                                color = colormap(row["insecurity_score"])
                                fill_opacity = float(row['opacity'])
                                
                                # Texte du popup avec informations détaillées
                                count = int(row['point_count']) if not pd.isna(row['point_count']) else 0
                                popup_txt = f"""
                                <div style='font-family: Arial; font-size: 12px;'>
                                    <b>Score d'insécurité:</b> {row['insecurity_score']:.1f}%<br>
                                    <b>Nombre de points:</b> {count}<br>
                                    <b>Opacité:</b> {fill_opacity:.2f}
                                </div>
                                """

                                # Ajouter l'hexagone
                                folium.Polygon(
                                    locations=boundary,
                                    color=color,
                                    fill=True,
                                    fill_color=color,
                                    fill_opacity=fill_opacity,
                                    weight=1.2,
                                    opacity=0.8,
                                    popup=folium.Popup(popup_txt, max_width=280)
                                ).add_to(m)
                                
                                hexagones_ajoutes += 1
                                
                            except Exception as e:
                                st.warning(f"Erreur pour un hexagone : {str(e)}")
                                continue

                        # Ajouter la colormap à la carte
                        colormap.add_to(m)
                        
                        # Légende améliorée pour l'opacité
                        min_count = int(hex_stats['point_count'].min())
                        max_count = int(hex_stats['point_count'].max())
                        
                        legend_html = f'''
                        <div style="position: fixed; 
                                    bottom: 50px; right: 50px; width: 260px; height: 190px; 
                                    background-color: white; border:2px solid grey; z-index:9999; 
                                    font-size:13px; padding: 12px; border-radius: 5px;
                                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        <p style="margin: 0 0 10px 0; font-weight: bold; font-size: 14px;">📊 Densité des points</p>
                        <div style="margin: 5px 0;">
                            <span style="background-color: #3498db; opacity: 0.12; padding: 2px 15px; border: 1px solid #2980b9;">▮▮▮</span>
                            <span style="margin-left: 8px;">1 point (quasi invisible)</span>
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="background-color: #3498db; opacity: 0.35; padding: 2px 15px; border: 1px solid #2980b9;">▮▮▮</span>
                            <span style="margin-left: 8px;">2-3 points (faible)</span>
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="background-color: #3498db; opacity: 0.60; padding: 2px 15px; border: 1px solid #2980b9;">▮▮▮</span>
                            <span style="margin-left: 8px;">4-6 points (moyen)</span>
                        </div>
                        <div style="margin: 5px 0;">
                            <span style="background-color: #3498db; opacity: 0.85; padding: 2px 15px; border: 1px solid #2980b9;">▮▮▮</span>
                            <span style="margin-left: 8px;">7+ points (fort)</span>
                        </div>
                        <hr style="margin: 8px 0; border: none; border-top: 1px solid #ddd;">
                        <p style="margin: 5px 0; font-size: 11px; color: #666;">
                            <b>Plage:</b> {min_count} - {max_count} points/hexagone
                        </p>
                        </div>
                        '''
                        m.get_root().html.add_child(folium.Element(legend_html))
                        
                        # Message de confirmation
                        st.success(f"✅ {hexagones_ajoutes} hexagones affichés sur la carte")
                        
                        # Afficher la carte
                        folium_static(m, width=900, height=600)

                        # Statistiques détaillées
                        st.subheader("📊 Statistiques")
                        col_stat1, col_stat2, col_stat3 = st.columns(3)
                        
                        with col_stat1:
                            st.metric("Hexagones affichés", f"{len(hex_stats):,}")
                        
                        with col_stat2:
                            avg_score = hex_stats['insecurity_score'].mean()
                            st.metric("Score moyen d'insécurité", f"{avg_score:.1f}%")
                        
                        with col_stat3:
                            total_points = hex_stats['point_count'].sum()
                            st.metric("Total de points", f"{int(total_points):,}")
                        
            except ImportError:
                st.error("❌ Le module `h3` n'est pas installé. Installez-le avec : `pip install h3`")
            except Exception as e:
                st.error(f"❌ Erreur lors de la création des hexagones : {str(e)}")
                st.exception(e)
                st.info("💡 Conseil : vérifiez le CSV (colonnes lat/lon, valeurs), et l'installation de `h3`.")

        # === VISUALISATION NORMALE (POINTS) ===
        else:
            st.subheader("Carte des points individuels")
            
            if df_map.empty:
                st.warning("Aucune donnée à afficher avec les filtres sélectionnés")
            else:
                # Créer la carte avec folium
                center_lat = float(df_map["lat"].median())
                center_lon = float(df_map["lon"].median())
                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=12,
                    tiles='OpenStreetMap'
                )
                
                # Définir les couleurs selon le type de lieu
                color_dict = {
                    "Endroit insécurisant": "red",
                    "Endroit sécurisant": "green"
                }
                
                # Ajouter les points à la carte
                points_ajoutes = 0
                for idx, row in df_map.iterrows():
                    color = color_dict.get(row["type_lieu"], "blue")
                    
                    # Créer le popup
                    popup_text = f"<b>Type:</b> {row['type_lieu']}<br>"
                    popup_text += f"<b>Genre:</b> {row.get('genre', 'N/A')}<br>"
                    
                    if show_comments and 'commentaire' in row and pd.notna(row['commentaire']):
                        popup_text += f"<b>Commentaire:</b> {row['commentaire']}"
                    
                    folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=4,
                        popup=folium.Popup(popup_text, max_width=300),
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=0.7
                    ).add_to(m)
                    points_ajoutes += 1
                
                st.success(f"✅ {points_ajoutes} points affichés sur la carte")
                
                # Afficher la carte
                folium_static(m, width=900, height=600)
                
                # Statistiques
                st.subheader("📊 Statistiques")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Points affichés", f"{len(df_map):,}")
                
                with col2:
                    if sentiment == "Tous":
                        pct_insecure = (df_map['type_lieu'] == 'Endroit insécurisant').mean() * 100
                        st.metric("% Insécurisants", f"{pct_insecure:.1f}%")
                    else:
                        st.metric("Type affiché", sentiment)
                
                with col3:
                    if genre_filter == "Tous":
                        pct_femmes = (df_map['genre'] == 'Femme').mean() * 100
                        st.metric("% Femmes", f"{pct_femmes:.1f}%")
                    else:
                        st.metric("Genre affiché", genre_filter)
            

# =============================
# CAS 5 : Croisement de questions
# =============================

with main_tab2:
    plt.close('all')
    
    st.header("🔀 Croisement de questions")
    st.write("Analysez les relations entre deux questions en filtrant sur une réponse spécifique.")
    
    # ===========================
    # 1. SÉLECTION DES QUESTIONS
    # ===========================
    st.subheader("1️⃣ Choisissez les questions à croiser")
    
    all_columns = list(questions_specs.keys())
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        st.markdown("**Question 1 (filtre)**")
        q1_options = [(q, f"{q} - {questions_specs[q]['label']}") for q in all_columns]
        selected_q1_id = st.selectbox(
            "Question de filtrage :",
            options=[opt[0] for opt in q1_options],
            format_func=lambda x: [opt[1] for opt in q1_options if opt[0] == x][0],
            key="q1_cross",
            label_visibility="collapsed"
        )
        q1_info = questions_specs[selected_q1_id]
        
        # Sélection sous-question et réponse pour Q1
        if q1_info["type"] == "likert":
            sub_questions = list(q1_info["labels"].keys())
            col_q1 = st.selectbox(
                "Sous-question :",
                sub_questions,
                format_func=lambda x: q1_info["labels"][x],
                key="subq1_cross"
            )
            reponses_q1 = list(q1_info["scale_labels"].values())
            selected_reponse_q1 = st.selectbox("Réponse :", reponses_q1, key="reponse_q1")
        elif q1_info["type"] == "multi":
            sub_questions = list(q1_info["labels"].keys())
            col_q1 = st.selectbox(
                "Sous-question :",
                sub_questions,
                format_func=lambda x: q1_info["labels"][x],
                key="subq1_cross"
            )
            possible = plr[col_q1].dropna().unique().tolist()
            selected_reponse_q1 = "Oui" if "Oui" in possible else (1 if 1 in possible else possible[0])
            st.info(f"Filtre automatique : **{selected_reponse_q1}**")
        else:
            col_q1 = selected_q1_id
            reponses_q1 = plr[col_q1].dropna().unique().tolist()
            selected_reponse_q1 = st.selectbox("Réponse :", reponses_q1, key="reponse_q1")
    
    with col_sel2:
        st.markdown("**Question 2 (à analyser)**")
        q2_options = [(q, f"{q} - {questions_specs[q]['label']}") for q in all_columns if q != selected_q1_id]
        selected_q2_id = st.selectbox(
            "Question à analyser :",
            options=[opt[0] for opt in q2_options],
            format_func=lambda x: [opt[1] for opt in q2_options if opt[0] == x][0],
            key="q2_cross",
            label_visibility="collapsed"
        )
        q2_info = questions_specs[selected_q2_id]
        
        # Sélection pour Q2
        if q2_info["type"] == "likert":
            sub_questions2 = list(q2_info["labels"].keys())
            col_q2 = st.selectbox(
                "Sous-question :",
                sub_questions2,
                format_func=lambda x: q2_info["labels"][x],
                key="subq2_cross"
            )
        elif q2_info["type"] == "multi":
            col_q2 = selected_q2_id
        else:
            col_q2 = selected_q2_id
    
    # ===========================
    # 2. OPTIONS D'ANALYSE
    # ===========================
    st.subheader("2️⃣ Options d'analyse")
    
    col_opt1, col_opt2 = st.columns(2)
    
    with col_opt1:
        st.write(f"**Pondération :** {'✅ Activée' if weight_col else '❌ Désactivée'}")
    
    with col_opt2:
        compare_demo = st.checkbox("📊 Comparer par variable sociodémographique", value=False)
    
    selected_demo = None
    if compare_demo:
        demo_options = {
            "genre": "Genre", "age": "Âge", "formation": "Formation",
            "revenu": "Revenu", "cat_domicile": "Typologie du domicile",
            "type_menage": "Composition du ménage"
        }
        selected_demo = st.selectbox(
            "Variable de comparaison :",
            options=list(demo_options.keys()),
            format_func=lambda x: demo_options[x],
            key="demo_comp"
        )
    
    # ===========================
    # 3. ANALYSE
    # ===========================
    if st.button("🔍 Analyser le croisement", key="btn_analyse", type="primary"):
        with st.spinner("🔄 Analyse en cours..."):
            
            if col_q1 not in plr.columns:
                st.error(f"❌ Colonne **{col_q1}** introuvable")
                st.stop()
            
            # AVEC COMPARAISON DÉMOGRAPHIQUE
            if compare_demo and selected_demo:
                st.subheader(f"📊 Comparaison par {demo_options[selected_demo]}")
                
                demo_cats = plr[selected_demo].dropna().unique().tolist()
                if selected_demo in order_dict:
                    demo_cats = [c for c in order_dict[selected_demo] if c in demo_cats]
                else:
                    demo_cats = sorted(demo_cats)
                
                tabs = st.tabs([f"{cat}" for cat in demo_cats])
                
                for tab, category in zip(tabs, demo_cats):
                    with tab:
                        plr_cat = plr[plr[selected_demo] == category].copy()
                        st.info(f"📊 **{len(plr_cat)} répondants**")
                        
                        if q2_info["type"] == "multi":
                            results = process_multi_question_cross(plr_cat, col_q1, selected_reponse_q1, q2_info, weight_col)
                            if results.empty:
                                st.warning(f"⚠️ Aucune donnée pour **{category}**")
                            else:
                                q1_label = q1_info["labels"].get(col_q1, q1_info["label"]) if q1_info["type"] in ["likert", "multi"] else q1_info["label"]
                                title = f"{category} | '{selected_reponse_q1}' à '{q1_label}'"
                                fig = plot_multi_cross_results(results, title, figsize=(12, 8))
                                if fig:
                                    st.pyplot(fig)
                        else:
                            result = analyse_croisee_questions(plr_cat, col_q1, selected_reponse_q1, col_q2, weight_col)
                            if result is None or result.empty:
                                st.warning(f"⚠️ Aucune donnée pour **{category}**")
                            else:
                                q1_label = q1_info["labels"].get(col_q1, col_q1) if q1_info["type"] in ["likert", "multi"] else q1_info["label"]
                                q2_label = q2_info["labels"].get(col_q2, col_q2) if q2_info["type"] in ["likert", "multi"] else q2_info["label"]
                                
                                order = None
                                if q2_info["type"] == "likert" and "scale_labels" in q2_info:
                                    order = [label for _, label in sorted(q2_info["scale_labels"].items())]
                                elif col_q2 in order_dict:
                                    order = order_dict[col_q2]
                                
                                fig = plot_croisement_questions(
                                    result_df=result,
                                    question1_label=f"{category} | {q1_label}",
                                    reponse1=selected_reponse_q1,
                                    question2_label=q2_label,
                                    order=order
                                )
                                st.pyplot(fig)
            
            # SANS COMPARAISON DÉMOGRAPHIQUE
            else:
                st.subheader("📊 Résultats de l'analyse croisée")
                
                if q2_info["type"] == "multi":
                    results = process_multi_question_cross(plr, col_q1, selected_reponse_q1, q2_info, weight_col)
                    if results.empty:
                        st.warning(f"⚠️ Aucun répondant n'a choisi '{selected_reponse_q1}'")
                    else:
                        q1_label = q1_info["labels"].get(col_q1, q1_info["label"]) if q1_info["type"] in ["likert", "multi"] else q1_info["label"]
                        title = f"'{q2_info['label']}' pour '{selected_reponse_q1}' à '{q1_label}'"
                        fig = plot_multi_cross_results(results, title)
                        if fig:
                            st.pyplot(fig)
                else:
                    result = analyse_croisee_questions(plr, col_q1, selected_reponse_q1, col_q2, weight_col)
                    if result is None or result.empty:
                        st.warning("⚠️ Aucune donnée disponible")
                    else:
                        q1_label = q1_info["labels"].get(col_q1, col_q1) if q1_info["type"] in ["likert", "multi"] else q1_info["label"]
                        q2_label = q2_info["labels"].get(col_q2, col_q2) if q2_info["type"] in ["likert", "multi"] else q2_info["label"]
                        
                        order = None
                        if q2_info["type"] == "likert" and "scale_labels" in q2_info:
                            order = [label for _, label in sorted(q2_info["scale_labels"].items())]
                        elif col_q2 in order_dict:
                            order = order_dict[col_q2]
                        
                        fig = plot_croisement_questions(
                            result_df=result,
                            question1_label=q1_label,
                            reponse1=selected_reponse_q1,
                            question2_label=q2_label,
                            order=order
                        )
                        st.pyplot(fig)

# Footer
st.markdown("---")
st.caption("Interface développée pour visualiser les résultats d'une enquête sur la mobilité et la sécurité nocturne.")

# ===========================
# Footer
# ===========================
st.markdown("---")
st.caption("Interface développée pour visualiser les résultats d'une enquête sur la mobilité et la sécurité nocturne.")

