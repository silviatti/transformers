# coding=utf-8
# Copyright 2018 The HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Convert RoBERTa checkpoint."""


import argparse

from transformers import logging
from transformers.modeling_prophetnet import ProphetNetForConditionalGeneration
from transformers.modeling_xlm_prophetnet import XLMProphetNetForConditionalGeneration

# transformers_old should correspond to branch `save_old_prophetnet_model_structure` here
from transformers_old.modeling_prophetnet import (
    ProphetNetForConditionalGeneration as ProphetNetForConditionalGenerationOld,
)
from transformers_old.modeling_xlm_prophetnet import (
    XLMProphetNetForConditionalGeneration as XLMProphetNetForConditionalGenerationOld,
)


logger = logging.get_logger(__name__)
logging.set_verbosity_info()


def convert_prophetnet_checkpoint_to_pytorch(prophetnet_checkpoint_path: str, pytorch_dump_folder_path: str):
    """
    Copy/paste/tweak prohpetnet's weights to our prophetnet structure.
    """
    if "xprophetnet" in prophetnet_checkpoint_path:
        prophet_old = XLMProphetNetForConditionalGenerationOld.from_pretrained(prophetnet_checkpoint_path)
        prophet, loading_info = XLMProphetNetForConditionalGeneration.from_pretrained(
            prophetnet_checkpoint_path, output_loading_info=True
        )
    else:
        prophet_old = ProphetNetForConditionalGenerationOld.from_pretrained(prophetnet_checkpoint_path)
        prophet, loading_info = ProphetNetForConditionalGeneration.from_pretrained(
            prophetnet_checkpoint_path, output_loading_info=True
        )

    mapping = {
        "ngram_self_attn_layer_norm": "self_attn_layer_norm",
        "cross_attn": "encoder_attn",
        "cross_attn_layer_norm": "encoder_attn_layer_norm",
        "feed_forward_layer_norm": "final_layer_norm",
        "feed_forward": "",
        "intermediate": "fc1",
        "output": "fc2",
        "key_proj_bias": "bias_k",
        "value_proj_bias": "bias_v",
        "key_proj_weight": "k_proj_weight",
        "value_proj_weight": "v_proj_weight",
        "query_proj_weight": "q_proj_weight",
        "key_proj": "k_proj",
        "value_proj": "v_proj",
        "query_proj": "q_proj",
        "word_embeddings": "embed_tokens",
        "embeddings_layer_norm": "emb_layer_norm",
    }

    for key in loading_info["missing_keys"]:
        attributes = key.split(".")

        if attributes[0] == "lm_head":
            model = prophet
            old_model = prophet_old
        else:
            model = prophet.prophetnet
            old_model = prophet_old.model

        is_key_init = False
        for attribute in attributes:
            if attribute in mapping:
                old_attribute = mapping[attribute]
            else:
                old_attribute = attribute

            if attribute == "weight":
                assert old_model.weight.shape == model.weight.shape, "Shapes have to match!"
                model.weight = old_model.weight
                logger.info(f"{attribute} is initialized.")
                is_key_init = True
                break
            elif attribute == "bias":
                assert old_model.bias.shape == model.bias.shape, "Shapes have to match!"
                model.bias = old_model.bias
                logger.info(f"{attribute} is initialized")
                is_key_init = True
                break
            elif attribute in [
                "in_proj_weight",
                "key_proj_weight",
                "value_proj_weight",
                "query_proj_weight",
                "in_proj_bias",
                "key_proj_bias",
                "value_proj_bias",
            ]:
                old_model_weight = getattr(old_model, old_attribute)
                assert getattr(model, attribute).shape == old_model_weight.shape, "Shapes have to match!"
                setattr(model, attribute, old_model_weight)
                is_key_init = True
                break

            if attribute.isdigit():
                model = model[int(attribute)]
                old_model = old_model[int(old_attribute)]
            else:
                model = getattr(model, attribute)

                if old_attribute == "":
                    old_model = old_model
                else:
                    old_model = getattr(old_model, old_attribute)

        if not is_key_init:
            raise ValueError(f"{key} was not correctly initialized!")

    print(f"Saving model to {pytorch_dump_folder_path}")
    prophet.save_pretrained(pytorch_dump_folder_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Required parameters
    parser.add_argument(
        "--prophetnet_checkpoint_path", default=None, type=str, required=True, help="Path the official PyTorch dump."
    )
    parser.add_argument(
        "--pytorch_dump_folder_path", default=None, type=str, required=True, help="Path to the output PyTorch model."
    )
    args = parser.parse_args()
    convert_prophetnet_checkpoint_to_pytorch(args.prophetnet_checkpoint_path, args.pytorch_dump_folder_path)
