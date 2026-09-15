import unittest

from datasets import Dataset

from scripts.train_phase_01 import CausalDataCollator, tokenize_dataset


class CausalDataCollatorTests(unittest.TestCase):
    def test_pads_inputs_and_masks_labels(self) -> None:
        collator = CausalDataCollator(pad_token_id=9)
        batch = collator(
            [
                {"input_ids": [1, 2], "attention_mask": [1, 1], "labels": [-100, 2]},
                {"input_ids": [3], "attention_mask": [1], "labels": [3]},
            ]
        )
        self.assertEqual(batch["input_ids"].tolist(), [[1, 2], [3, 9]])
        self.assertEqual(batch["labels"].tolist(), [[-100, 2], [3, -100]])

    def test_keeps_requested_count_after_discarding_long_examples(self) -> None:
        class TokenizerStub:
            def apply_chat_template(self, messages, tokenize, add_generation_prompt, **kwargs):
                return [token for message in messages for token in message["content"]] + ([0] if add_generation_prompt else [])

        dataset = Dataset.from_list(
            [
                {"messages": [{"content": list(range(8))}, {"content": [9]}]},
                {"messages": [{"content": [1]}, {"content": [2, 3]}]},
                {"messages": [{"content": [3]}, {"content": [4, 5]}]},
            ]
        )
        result = tokenize_dataset(dataset, TokenizerStub(), max_sequence_length=4, requested_samples=2)
        self.assertEqual(len(result), 2)
