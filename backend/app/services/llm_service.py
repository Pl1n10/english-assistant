import httpx
from typing import List, Dict, Any, Optional

from app.config import settings
from app.models import Message, MessageRole


class LLMService:
    """LLM per assistente lezioni d'inglese: triage richieste, proposta slot, conferme."""

    def __init__(self):
        self.api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        self.api_url = getattr(settings, "OPENROUTER_API_URL", "https://openrouter.ai/api/v1")
        self.model = getattr(settings, "DEFAULT_MODEL", "openai/gpt-4o-mini")

    def _build_system_prompt(self) -> str:
        return (
            "Sei un assistente per la gestione di lezioni d'inglese via WhatsApp.\n"
            "Obiettivi: capire la richiesta dello studente, raccogliere nome/email/livello, proporre slot compatibili, "
            "confermare e riassumere i dettagli della lezione (data, ora, durata, prezzo indicativo).\n"
            "Stile: cordiale, sintetico, in italiano; usa elenchi quando utile. Chiedi conferma esplicita prima di fissare una lezione.\n"
            "Se lo studente non fornisce dati chiave, chiedili con domande chiare (es. disponibilità giorni/ore, durata preferita).\n"
            "Non inventare informazioni non date. Quando c'è conferma, restituisci anche un oggetto JSON compatto con chiave 'lesson_request' "
            "{'student_name': '...', 'student_email': '...', 'student_level': '...', 'notes': '...', "
            "'desired_duration': 60, 'timezone': 'Europe/Rome'} se i dati sono disponibili."
        )

    def _format_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        role_map = {
            MessageRole.USER: "user",
            MessageRole.ASSISTANT: "assistant",
            MessageRole.TEACHER: "assistant",  # i messaggi del docente li trattiamo come assistant
            MessageRole.SYSTEM: "system",
        }
        formatted: List[Dict[str, str]] = []
        for m in messages:
            formatted.append({"role": role_map.get(m.role, "user"), "content": m.content})
        return formatted

    def _extract_json_block(self, text: str, key: str) -> Optional[Dict[str, Any]]:
        """Estrae un JSON minimal contenente la chiave `key` (es. 'lesson_request') dal testo del modello."""
        import json
        start = text.find(f'{{"{key}"')
        if start == -1:
            start = text.find(f"{{'{key}'")
            if start == -1:
                return None
        brace = 0
        end = start
        for i, ch in enumerate(text[start:]):
            if ch == "{":
                brace += 1
            elif ch == "}":
                brace -= 1
                if brace == 0:
                    end = start + i + 1
                    break
        try:
            payload = json.loads(text[start:end].replace("'", '"'))
            return payload.get(key)
        except Exception:
            return None

    async def generate_response(
        self,
        message_content: str,
        conversation_history: List[Message],
    ) -> Dict[str, Any]:
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages += self._format_history(conversation_history[-10:])
        messages.append({"role": "user", "content": message_content})

        # Se non è configurata la chiave, rispondi in modo statico (fallback dev)
        if not self.api_key:
            reply = (
                "Ciao! Posso aiutarti a fissare una lezione d'inglese. "
                "Dimmi quando saresti disponibile (giorni/orari) e la durata preferita (es. 60 minuti)."
            )
            return {"message": reply, "lesson_request": None, "raw_response": reply}

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.5,
                        "max_tokens": 800,
                    },
                )
                r.raise_for_status()
                data = r.json()
                assistant_message = data["choices"][0]["message"]["content"]

                lesson_req = self._extract_json_block(assistant_message, "lesson_request")
                return {
                    "message": assistant_message,
                    "lesson_request": lesson_req,
                    "raw_response": assistant_message,
                }
        except httpx.HTTPError as e:
            return {
                "message": "Al momento ho difficoltà tecniche. Riprova tra poco.",
                "lesson_request": None,
                "error": str(e),
            }
