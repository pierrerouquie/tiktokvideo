"""
Module de récupération automatique de médias (vidéos/images).
Utilise l'API Pexels (gratuite) pour trouver du contenu en rapport avec le texte.
Extrait automatiquement les mots-clés du script pour la recherche.
"""
import os
import re
import json
import random
import hashlib
import requests
from pathlib import Path
from typing import Optional


# Mots vides français et anglais à exclure de l'extraction de mots-clés
STOP_WORDS_FR = {
    "le", "la", "les", "un", "une", "des", "de", "du", "au", "aux",
    "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "quoi",
    "ce", "cette", "ces", "mon", "ma", "mes", "ton", "ta", "tes",
    "son", "sa", "ses", "notre", "votre", "leur", "leurs",
    "je", "tu", "il", "elle", "nous", "vous", "ils", "elles", "on",
    "ne", "pas", "plus", "jamais", "rien", "tout", "tous", "toute",
    "est", "sont", "être", "avoir", "fait", "faire", "dit", "dire",
    "dans", "sur", "sous", "avec", "sans", "pour", "par", "entre",
    "très", "bien", "aussi", "comme", "même", "encore", "déjà",
    "ici", "là", "alors", "puis", "après", "avant", "quand",
    "comment", "pourquoi", "où", "si", "oui", "non",
}

STOP_WORDS_EN = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "shall",
    "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "what", "which", "who",
    "in", "on", "at", "to", "for", "with", "from", "by", "about",
    "and", "or", "but", "not", "no", "so", "if", "then",
    "very", "just", "also", "how", "when", "where", "why",
}

ALL_STOP_WORDS = STOP_WORDS_FR | STOP_WORDS_EN


class MediaFetcher:
    """Récupère automatiquement des vidéos/images de stock via Pexels API."""

    PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
    PEXELS_PHOTO_URL = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "assets/backgrounds"):
        """
        Args:
            api_key: Clé API Pexels (gratuite sur https://www.pexels.com/api/).
                     Si None, cherche dans la variable d'env PEXELS_API_KEY.
            cache_dir: Dossier de cache pour les fichiers téléchargés.
        """
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY", "")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_available(self) -> bool:
        """Vérifie si l'API Pexels est configurée."""
        return len(self.api_key) > 10

    def extract_keywords(self, text: str, max_keywords: int = 3) -> list[str]:
        """
        Extrait les mots-clés les plus pertinents d'un texte.
        Utilise une approche simple par fréquence après filtrage des mots vides.

        Args:
            text: Le texte source (script de la vidéo)
            max_keywords: Nombre max de mots-clés à retourner

        Returns:
            Liste de mots-clés triés par pertinence
        """
        # Nettoyer le texte
        clean = re.sub(r"[^\w\s]", " ", text.lower())
        words = clean.split()

        # Filtrer les mots vides et les mots trop courts
        meaningful = [w for w in words if w not in ALL_STOP_WORDS and len(w) > 3]

        # Compter les fréquences
        freq: dict[str, int] = {}
        for w in meaningful:
            freq[w] = freq.get(w, 0) + 1

        # Trier par fréquence décroissante, puis par longueur (mots plus longs = plus spécifiques)
        sorted_words = sorted(freq.keys(), key=lambda w: (freq[w], len(w)), reverse=True)

        return sorted_words[:max_keywords]

    def search_videos(
        self,
        query: str,
        orientation: str = "portrait",
        per_page: int = 5,
        min_duration: int = 5,
    ) -> list[dict]:
        """
        Cherche des vidéos sur Pexels.

        Args:
            query: Termes de recherche
            orientation: "portrait" (9:16), "landscape" (16:9), "square"
            per_page: Nombre de résultats
            min_duration: Durée minimum en secondes

        Returns:
            Liste de dicts avec {url, width, height, duration, thumbnail}
        """
        if not self.is_available:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
            "size": "medium",
        }

        try:
            print(f"🔍 Recherche Pexels vidéos : '{query}'...")
            resp = requests.get(self.PEXELS_VIDEO_URL, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"⚠️ Erreur Pexels vidéo : {e}")
            return []

        results = []
        for video in data.get("videos", []):
            if video.get("duration", 0) < min_duration:
                continue

            # Chercher le fichier HD le plus adapté
            best_file = None
            for vf in video.get("video_files", []):
                w, h = vf.get("width", 0), vf.get("height", 0)
                if h >= 720 and vf.get("link"):
                    if best_file is None or h > best_file.get("height", 0):
                        best_file = {
                            "url": vf["link"],
                            "width": w,
                            "height": h,
                        }

            if best_file:
                results.append({
                    **best_file,
                    "duration": video.get("duration", 0),
                    "thumbnail": video.get("image", ""),
                    "pexels_id": video.get("id"),
                })

        print(f"   → {len(results)} vidéo(s) trouvée(s)")
        return results

    def search_photos(
        self,
        query: str,
        orientation: str = "portrait",
        per_page: int = 5,
    ) -> list[dict]:
        """
        Cherche des photos sur Pexels (fallback si pas de vidéos).

        Returns:
            Liste de dicts avec {url, width, height}
        """
        if not self.is_available:
            return []

        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
            "size": "large",
        }

        try:
            print(f"🔍 Recherche Pexels photos : '{query}'...")
            resp = requests.get(self.PEXELS_PHOTO_URL, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"⚠️ Erreur Pexels photo : {e}")
            return []

        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            url = src.get("large2x") or src.get("large") or src.get("original")
            if url:
                results.append({
                    "url": url,
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "pexels_id": photo.get("id"),
                })

        print(f"   → {len(results)} photo(s) trouvée(s)")
        return results

    def download_file(self, url: str, filename: Optional[str] = None) -> str:
        """
        Télécharge un fichier et le met en cache.

        Returns:
            Chemin local du fichier téléchargé
        """
        if not filename:
            ext = ".mp4" if "video" in url or url.endswith(".mp4") else ".jpg"
            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
            filename = f"pexels_{url_hash}{ext}"

        filepath = self.cache_dir / filename
        if filepath.exists():
            print(f"📦 Cache hit : {filepath}")
            return str(filepath)

        try:
            print(f"⬇️ Téléchargement : {url[:80]}...")
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✅ Téléchargé : {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"❌ Erreur téléchargement : {e}")
            return ""

    def auto_fetch_background(
        self,
        text: str,
        prefer_video: bool = True,
        orientation: str = "portrait",
    ) -> dict:
        """
        Pipeline automatique : extrait les mots-clés du texte, cherche
        un média sur Pexels, le télécharge, et retourne le chemin local.

        Args:
            text: Le script/texte de la vidéo
            prefer_video: Préférer les vidéos aux images
            orientation: "portrait" pour TikTok

        Returns:
            Dict avec {path, type, keywords} ou {path: "", type: "none"} si échec
        """
        if not self.is_available:
            print("⚠️ Pas de clé API Pexels → fond uni par défaut")
            return {"path": "", "type": "none", "keywords": []}

        # Extraire les mots-clés
        keywords = self.extract_keywords(text)
        if not keywords:
            keywords = ["abstract", "background"]

        query = " ".join(keywords)
        print(f"🔑 Mots-clés extraits : {keywords}")

        # Chercher des vidéos d'abord
        if prefer_video:
            videos = self.search_videos(query, orientation=orientation)
            if videos:
                chosen = random.choice(videos[:3])  # Varier un peu
                local_path = self.download_file(chosen["url"])
                if local_path:
                    return {"path": local_path, "type": "video", "keywords": keywords}

        # Fallback sur les photos
        photos = self.search_photos(query, orientation=orientation)
        if photos:
            chosen = random.choice(photos[:3])
            local_path = self.download_file(chosen["url"])
            if local_path:
                return {"path": local_path, "type": "image", "keywords": keywords}

        # Essayer avec des mots-clés plus génériques
        if len(keywords) > 1:
            print("🔄 Retry avec mot-clé unique...")
            fallback_query = keywords[0]
            photos = self.search_photos(fallback_query, orientation=orientation)
            if photos:
                chosen = random.choice(photos[:3])
                local_path = self.download_file(chosen["url"])
                if local_path:
                    return {"path": local_path, "type": "image", "keywords": [fallback_query]}

        print("⚠️ Aucun média trouvé → fond uni par défaut")
        return {"path": "", "type": "none", "keywords": keywords}
