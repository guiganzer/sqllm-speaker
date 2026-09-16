"""Autor SQL local baseado no adapter QLoRA especializado."""

from __future__ import annotations

from pathlib import Path

from llm_to_sql.evaluation import normalize_model_output


DEFAULT_MODEL_ID = "Qwen/Qwen3-4B-Thinking-2507"
DEFAULT_MODEL_REVISION = "768f209d9ea81521153ed38c47d515654e938aea"


def build_author_messages(
    question: str,
    schema_ddl: str,
    repair_error: str | None = None,
    previous_sql: str | None = None,
) -> list[dict[str, str]]:
    """Monta a conversa mínima e estruturada para geração ou reparo SQL."""

    if not question.strip():
        raise ValueError("A pergunta não pode estar vazia.")
    if not schema_ddl.strip():
        raise ValueError("O schema não pode estar vazio.")
    system = "Você é um assistente especializado em SQL. Gere somente uma consulta SQL compatível com o schema fornecido. Não explique a resposta."
    user = f"<schema>\n{schema_ddl}\n</schema>\n<pergunta>\n{question.strip()}\n</pergunta>"
    if repair_error:
        if not previous_sql or not previous_sql.strip():
            raise ValueError("previous_sql é obrigatório durante reparo.")
        user += (
            f"\n<consulta_anterior>\n{previous_sql.strip()}\n</consulta_anterior>"
            f"\n<erro_sanitizado>\n{repair_error.strip()}\n</erro_sanitizado>"
            "\nCorrija somente o defeito informado. Use exclusivamente relações do schema e responda somente SQL."
        )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def render_author_prompt(tokenizer, messages: list[dict[str, str]]) -> str:
    try:
        return tokenizer.apply_chat_template(messages, enable_thinking=False, tokenize=False, add_generation_prompt=True)
    except TypeError:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


class PhaseOneSqlAuthor:
    """Carregamento preguiçoso do adapter 4-bit para inferência local."""

    def __init__(
        self,
        *,
        adapter_path: Path,
        model_id: str = DEFAULT_MODEL_ID,
        model_revision: str = DEFAULT_MODEL_REVISION,
        max_new_tokens: int = 192,
    ) -> None:
        if not adapter_path.is_dir():
            raise ValueError(f"Adapter não encontrado: {adapter_path}")
        if not 16 <= max_new_tokens <= 512:
            raise ValueError("max_new_tokens deve estar entre 16 e 512.")
        self.adapter_path = adapter_path
        self.model_id = model_id
        self.model_revision = model_revision
        self.max_new_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None

    def generate(
        self,
        question: str,
        schema_ddl: str,
        repair_error: str | None = None,
        previous_sql: str | None = None,
    ) -> str:
        return self.generate_candidates(
            question,
            schema_ddl,
            count=1,
            repair_error=repair_error,
            previous_sql=previous_sql,
        )[0]

    def generate_candidates(
        self,
        question: str,
        schema_ddl: str,
        *,
        count: int = 3,
        repair_error: str | None = None,
        previous_sql: str | None = None,
    ) -> list[str]:
        if not 1 <= count <= 5:
            raise ValueError("count deve estar entre 1 e 5.")
        model, tokenizer = self._load()
        prompt = render_author_prompt(tokenizer, build_author_messages(question, schema_ddl, repair_error, previous_sql))
        encoded = tokenizer(prompt, return_tensors="pt")
        encoded = {key: value.to(model.device) for key, value in encoded.items()}
        import torch

        with torch.inference_mode():
            generated = model.generate(
                **encoded,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                num_beams=count,
                num_return_sequences=count,
                early_stopping=count > 1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        prompt_length = encoded["input_ids"].shape[1]
        candidates: list[str] = []
        for sequence in generated:
            raw_output = tokenizer.decode(sequence[prompt_length:], skip_special_tokens=True).strip()
            normalized = normalize_model_output(raw_output)
            if normalized and normalized not in candidates:
                candidates.append(normalized)
        if not candidates:
            raise RuntimeError("O autor não produziu candidato SQL.")
        return candidates

    def _load(self):
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA é obrigatória para o autor SQL local.")
        quantization = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, revision=self.model_revision)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            revision=self.model_revision,
            quantization_config=quantization,
            dtype=torch.bfloat16,
            device_map={"": 0},
        )
        self._model = PeftModel.from_pretrained(model, str(self.adapter_path))
        self._model.eval()
        self._tokenizer = tokenizer
        return self._model, self._tokenizer
