---
source_id: nccl-technical-blog
title: NVIDIA Deep Learning SDK Update for Volta Now Available
canonical_url: https://developer.nvidia.com/blog/nvidia-deep-learning-sdk-update-for-volta-now-available/
captured_at: '2026-06-26T01:57:04.300993+00:00'
content_hash: 78694cbd7ed9db0c17f72c8e3e86f08e162527db273af2289b24da37e7a7763b
---
# NVIDIA Deep Learning SDK Update for Volta Now Available

URL: https://developer.nvidia.com/blog/nvidia-deep-learning-sdk-update-for-volta-now-available/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="151" src="https://developer-blogs.nvidia.com/wp-content/uploads/2017/08/cudnn-nccl-featured.png" style="display: block; margin-bottom: 5px; clear: both;" title="cudnn nccl featured" width="270" />At GTC 2017, NVIDIA announced Volta optimized updates to the NVIDIA Deep Learning SDK. Today, we’re making these updates available as free downloads to...

Article Body:
Data Science

 

 
 

 

 
 

 

 
NVIDIA Deep Learning SDK Update for Volta Now Available

 
 

 

 

 Aug 08, 2017
 

 

 By 
Brad Nemire
 

 

 

 
 
 

 
 

 Like

 

 

 

 
 Discuss (0)
 

 

 

 

 

 

 

 

 

 
L

 
T

 
F

 
R

 
E

 
 

 

 

 

 

 

 

 
AI-Generated Summary

 

 

 

 

 

 

 

 

 
Like

 

 

 

 

 

 

 
Dislike

 

 

 

 

 

 

 

 

 
The NVIDIA Deep Learning SDK has been updated with Volta optimized features, available as free downloads to NVIDIA Developer Program members.
cuDNN 7 offers up to 2.5x faster training of ResNet50 and 3x faster training of NMT language translation LSTM RNNs on Tesla V100 compared to Tesla P100.
NCCL 2 delivers over 90% multi-node scaling efficiency using up to 8 GPU-accelerated servers and performs automatic topology detection for optimal communication paths.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 
At GTC 2017, NVIDIA announced Volta optimized updates to the 
NVIDIA Deep Learning SDK
. Today, we’re making these updates available as free downloads to members of the NVIDIA Developer Program.

Deep learning
 frameworks using NVIDIA 
cuDNN 7
 and 
NCCL 2
 can 
take advantage of new features and performance benefits of the Volta architecture.

cuDNN 7

Up to 2.5x faster training of ResNet50 and 3x faster training of NMT language translation 
LSTM
 
RNNs
 on Tesla V100 vs. Tesla P100

Accelerated 
convolutions
 using mixed-precision 
Tensor Cores
 operations on Volta GPUs

Grouped Convolutions for models such as ResNeXt and Xception and CTC (Connectionist Temporal Classification) loss layer for temporal classification tasks

NCCL 2

Delivers over 90% multi-node scaling efficiency using up to 8 GPU-accelerated servers

Performs automatic topology detection to determine optimal communication path

Optimized to achieve high bandwidth over PCIe and NVLink high-speed interconnect

Left:
 Caffe2 performance (images/sec), Tesla K80 + cuDNN 6 (FP32), Tesla P100 + cuDNN 6 (FP32), Tesla V100 + cuDNN 7 (FP16). ResNet50, Batch size: 64. 
Right:
 Microsoft Cognitive Toolkit multi-node scaling performance (images/sec), NVIDIA DGX-1 + cuDNN 6 (FP32), ResNet50, Batch size: 64

Learn more about Volta’s Tensor Cores and multi-node scaling of deep learning training

Inside Volta: The World’s Most Advanced Data Center GPU

Optimized inter-GPU collective operations with NCCL 2

Visit the 
cuDNN 7
 and 
NCCL 2
 product pages to learn more and download >

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Science
 | 
cuDNN
 | 
NCCL
 | 
News
 | 
Machine Learning & Artificial Intelligence
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Brad Nemire
 

 

 
 Brad Nemire leads the Developer Communications team at NVIDIA. Prior to NVIDIA, he worked at Arm on the Developer Relations team. Brad graduated from San Diego State University and currently resides in Silicon Valley.
 
 
 

 

 View all posts by Brad Nemire

 

 

 

 

 

 

 

 

 

 

 
Comments
