/*
 * ASoC Driver for Google's AIY Voice Bonnet
 *
 * Author: Alex Van Damme <atv@google.com>
 *         Copyright 2017
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * version 2 as published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 */

#include <linux/module.h>
#include <linux/platform_device.h>

#include <sound/core.h>
#include <sound/jack.h>
#include <sound/pcm.h>
#include <sound/pcm_params.h>
#include <sound/soc.h>
#include "rt5645.h"

#define PLATFORM_CLOCK 24576000

static struct snd_soc_jack headset_jack;

static struct snd_soc_jack_pin headset_jack_pin = {
	.pin = "Headphone",
	.mask = 0xFFFFF,
	.invert = 0
};

static int snd_rpi_aiy_voicebonnet_init(struct snd_soc_pcm_runtime *rtd) {
	int ret;
	struct snd_soc_dai *codec_dai = asoc_rtd_to_codec(rtd, 0);

	rt5645_sel_asrc_clk_src(codec_dai->component,
		RT5645_DA_STEREO_FILTER |
		RT5645_AD_STEREO_FILTER |
		RT5645_DA_MONO_L_FILTER |
		RT5645_DA_MONO_R_FILTER,
		RT5645_CLK_SEL_I2S1_ASRC);

	ret = snd_soc_dai_set_sysclk(codec_dai, RT5645_SCLK_S_MCLK,
				     PLATFORM_CLOCK, SND_SOC_CLOCK_IN);
	if (ret < 0) {
		dev_err(rtd->card->dev, "can't set sysclk: %d\n", ret);
		return ret;
	}

	ret = snd_soc_card_jack_new(rtd->card, "Headphone Jack",
				    SND_JACK_HEADPHONE,
				    &headset_jack, &headset_jack_pin, 1);
	if (ret < 0) {
		dev_err(rtd->card->dev, "can't add headphone jack: %d\n", ret);
		return ret;
	}

	return rt5645_set_jack_detect(
		codec_dai->component, &headset_jack, NULL, NULL);
}

static int snd_rpi_aiy_voicebonnet_hw_params(
	struct snd_pcm_substream *substream, struct snd_pcm_hw_params *params) {
	int ret = 0;
	struct snd_soc_pcm_runtime *rtd = substream->private_data;
	struct snd_soc_dai *codec_dai = asoc_rtd_to_codec(rtd, 0);
	unsigned int freq = params_rate(params) * 512;

	/* set codec PLL source to the 24.576MHz (MCLK) platform clock */
	ret = snd_soc_dai_set_pll(codec_dai, 0, RT5645_PLL1_S_MCLK,
				  PLATFORM_CLOCK, freq);
	if (ret < 0) {
		dev_err(rtd->dev, "can't set codec pll: %d\n", ret);
		return ret;
	}

	ret = snd_soc_dai_set_sysclk(codec_dai, RT5645_SCLK_S_PLL1, freq,
				     SND_SOC_CLOCK_IN);
	if (ret < 0) {
		dev_err(rtd->dev, "can't set codec sysclk in: %d\n", ret);
		return ret;
	}

	ret = snd_soc_dai_set_sysclk(codec_dai, RT5645_SCLK_S_PLL1, freq,
				     SND_SOC_CLOCK_OUT);
	if (ret < 0) {
		dev_err(rtd->dev, "can't set codec sysclk out: %d\n", ret);
		return ret;
	}

	return ret;
}

static struct snd_soc_ops snd_rpi_aiy_voicebonnet_ops = {
	.hw_params = snd_rpi_aiy_voicebonnet_hw_params,
};

SND_SOC_DAILINK_DEFS(pcm,
	DAILINK_COMP_ARRAY(COMP_EMPTY()),
	DAILINK_COMP_ARRAY(COMP_CODEC(NULL, "rt5645-aif1")),
	DAILINK_COMP_ARRAY(COMP_EMPTY()));

static struct snd_soc_dai_link snd_rpi_aiy_voicebonnet_dai[] = {
	{
		.name = "rt5645",
		.stream_name = "Google AIY Voice Bonnet SoundCard HiFi",
		.dai_fmt = SND_SOC_DAIFMT_I2S |
			   SND_SOC_DAIFMT_NB_NF |
			   SND_SOC_DAIFMT_CBS_CFS,
		.ops = &snd_rpi_aiy_voicebonnet_ops,
		.init = snd_rpi_aiy_voicebonnet_init,
		SND_SOC_DAILINK_REG(pcm),
	},
};

static const struct snd_soc_dapm_widget voicebonnet_widgets[] = {
	SND_SOC_DAPM_HP("Headphone", NULL),
	SND_SOC_DAPM_SPK("Speaker", NULL),
	SND_SOC_DAPM_MIC("Int Mic", NULL),
};

static const struct snd_soc_dapm_route voicebonnet_audio_map[] = {
	{"Int Mic", NULL, "micbias1"},
	{"Int Mic", NULL, "micbias2"},
	{"IN1P", NULL, "Int Mic"},
	{"IN2P", NULL, "Int Mic"},
	{"Headphone", NULL, "HPOR"},
	{"Headphone", NULL, "HPOL"},
	{"Speaker", NULL, "SPOL"},
	{"Speaker", NULL, "SPOR"},
};

static const struct snd_kcontrol_new voicebonnet_controls[] = {
	SOC_DAPM_PIN_SWITCH("Headphone"),
	SOC_DAPM_PIN_SWITCH("Speaker"),
	SOC_DAPM_PIN_SWITCH("Int Mic"),
};

static struct snd_soc_card snd_rpi_aiy_voicebonnet = {
	.name = "snd_rpi_aiy_voicebonnet",
	.owner = THIS_MODULE,
	.dai_link = snd_rpi_aiy_voicebonnet_dai,
	.num_links = ARRAY_SIZE(snd_rpi_aiy_voicebonnet_dai),
	.dapm_routes = voicebonnet_audio_map,
	.num_dapm_routes = ARRAY_SIZE(voicebonnet_audio_map),
	.dapm_widgets = voicebonnet_widgets,
	.num_dapm_widgets = ARRAY_SIZE(voicebonnet_widgets),
	.controls = voicebonnet_controls,
	.num_controls = ARRAY_SIZE(voicebonnet_controls),
	.fully_routed = true,
};

static int snd_rpi_aiy_voicebonnet_probe(struct platform_device *pdev) {
	int ret = 0;
	struct snd_soc_dai_link *dai = &snd_rpi_aiy_voicebonnet_dai[0];
	struct snd_soc_card *card = &snd_rpi_aiy_voicebonnet;
	struct device *dev = &pdev->dev;
	struct device_node *i2s_node;

	card->dev = dev;

	if (dev->of_node) {
		dai->codecs->of_node = of_parse_phandle(dev->of_node,
		                                        "aiy-voicebonnet,audio-codec", 0);
		if (!dai->codecs->of_node) {
			dev_err(dev, "can't parse codec node\n");
			return -EINVAL;
		}

		i2s_node = of_parse_phandle(dev->of_node, "i2s-controller", 0);
		if (i2s_node) {
			dai->cpus->of_node = i2s_node;
			dai->platforms->of_node = i2s_node;
		}
	}

	ret = snd_soc_of_parse_card_name(card, "google,model");
	if (ret < 0) {
		dev_err(dev, "can't parse card name: %d\n", ret);
		return ret;
	}

	ret = devm_snd_soc_register_card(dev, card);
	if (ret < 0) {
		dev_err(dev, "can't register card: %d\n", ret);
		return ret;
	}

	return 0;
}

static const struct of_device_id snd_rpi_aiy_voicebonnet_of_match[] = {
	{
		.compatible = "google,aiy-voicebonnet",
	},
	{},
};
MODULE_DEVICE_TABLE(of, snd_rpi_aiy_voicebonnet_of_match);

static struct platform_driver snd_rpi_aiy_voicebonnet_driver = {
	.driver = {
		.name = "snd-soc-aiy-voicebonnet",
		.owner = THIS_MODULE,
		.of_match_table = snd_rpi_aiy_voicebonnet_of_match,
	},
	.probe = snd_rpi_aiy_voicebonnet_probe,
};
module_platform_driver(snd_rpi_aiy_voicebonnet_driver);

MODULE_AUTHOR("Alex Van Damme <atv@google.com>");
MODULE_AUTHOR("Dmitry Kovalev <dkovalev@google.com>");
MODULE_DESCRIPTION("ASoC Driver for Google AIY Voice Bonnet");
MODULE_LICENSE("GPL v2");
