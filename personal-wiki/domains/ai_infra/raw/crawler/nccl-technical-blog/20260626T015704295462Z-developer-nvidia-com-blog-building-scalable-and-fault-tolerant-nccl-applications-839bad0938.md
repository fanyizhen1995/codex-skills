---
source_id: nccl-technical-blog
title: Building Scalable and Fault-Tolerant NCCL Applications
canonical_url: https://developer.nvidia.com/blog/building-scalable-and-fault-tolerant-nccl-applications/
captured_at: '2026-06-26T01:57:04.295462+00:00'
content_hash: 839bad0938f8318147135b1ecbfb00598cdd1595739b41a6b05f16b6a9202b15
---
# Building Scalable and Fault-Tolerant NCCL Applications

URL: https://developer.nvidia.com/blog/building-scalable-and-fault-tolerant-nccl-applications/

RSS Summary:
<img alt="" class="webfeedsFeaturedVisual wp-post-image" height="432" src="https://developer-blogs.nvidia.com/wp-content/uploads/2025/07/neon-green-cube-768x432-png.webp" style="display: block; margin-bottom: 5px; clear: both;" title="neon-green-cube" width="768" />The NVIDIA Collective Communications Library (NCCL) provides communication APIs for low-latency and high-bandwidth collectives, enabling AI workloads to scale...

Article Body:
Networking / Communications

 

 
 

 

 
English
中文

 

 

 
Building Scalable and Fault-Tolerant NCCL Applications

 
 

 

 

 Nov 10, 2025
 

 

 By 
Luke Robison
, 
Jim Dinan
 and 
Misbah Mubarak
 

 

 

 
 
 

 
 

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

 

 

 

 

 

 

 

 

 
The NVIDIA Collective Communications Library (NCCL) enables dynamic application scaling by allowing communicators to be created or resized at runtime, supporting cost optimization and fault tolerance.
NCCL communicators can be configured to be non-blocking, enabling initialization to proceed in the background while continuing to process requests using the old communicator.
NCCL provides features like ncclCommShrink to simplify and optimize the process of removing faulted workers or scaling down, allowing applications to recover from faults without fully restarting the workload.

 

 
AI-generated content may summarize information incompletely. Verify important information. 
Learn more

 

 

 

 
 

The 
NVIDIA Collective Communications Library (NCCL)
 provides communication APIs for low-latency and high-bandwidth collectives, enabling AI workloads to scale from just a few GPUs on a single host to thousands of GPUs in a data center. This post discusses NCCL features that support run-time rescaling for cost optimization, as well as minimizing service downtime from faults by dynamically removing faulted workers.

Enabling scalable AI with NCCL

NCCL was introduced in 2015 to accelerate AI training using more than one GPU to train the model together. Over the next decade, training workloads have expanded to thousands of GPUs, and new models continue to increase in size and complexity. 

Today, both training and inference workloads rely on multi-GPU collectives that combine data parallelism, tensor parallelism, and expert parallelism to meet latency and throughput goals. NCCL collectives continue to form the communication backbone for these strategies, synchronizing computation across multiple workers (known as ranks) within a communicator.

Typically, a deep learning framework will perform a single initialization step at launch time to determine data sharding and assign each GPU their specific tasks in multiple dimensions of parallelism. However, as the model size and the need for parallelism in these inference engines increases, dynamically reallocating resources at runtime becomes attractive for minimizing operational footprint.  

A dynamically scalable inference engine can respond to increased user traffic by allocating additional GPUs and spreading the work across them, or relinquishing excess GPUs when traffic is low in order to optimize cost. These are examples of planned scaling events in which all parts of the system are working as designed. We’ll show that this pattern is useful for fault tolerance as well.

 

 
Figure 1. An inference cluster experiences increased traffic, which may impact response latency. The framework allocates two additional workers which join the communicator to share the load

How NCCL communicators enable dynamic application scaling

NCCL communicators were heavily inspired by 
MPI
 communicators. However, NCCL introduced important differences and new concepts to enable dynamic application scaling. 

NCCL communicators can be created from scratch by the application at any point during execution by passing a 
uniqueId
 to 
ncclCommInit
. In contrast, MPI creates a special communicator called 
MPI_COMM_WORLD
 during initialization, and all other communicators are subsets created with 
MPI_Comm_split
.

NCCL communicators can be configured to be non-blocking so that initialization functions may continue in the background.

In NCCL, the application chooses the assignment of ranks to communicator members, allowing applications to optimize the communicator layout.

Once a communicator is created, the set of members (ranks) is considered immutable. Therefore a NCCL application performing a scale-up operation executes a sequence much like a second initialization. A new 
uniqueId
 is obtained and shared across all ranks who pass it to 
ncclCommInit
. An optimized application may enable nonblocking mode to let the initialization work proceed in the background while continuing to process requests using the old communicator until the new one is ready.

Similarly, a scale-down can be implemented the same way using 
ncclCommInit
, or the application can call 
ncclCommShrink
, which has been optimized to reduce initialization time by re-using rank information from the old communicator. This optimization is particularly useful for very large communicators, but also provides a simplified API at any scale.

Fault-tolerant NCCL applications

Fault detection, attribution, and mitigation encompass a complex topic that spans the entire application stack from physical layers up to application layers. To learn more about faults and checkpoint recovery, see 
Ensuring Reliable Model Training on NVIDIA DGX Cloud
. To learn more about observability and fault-tolerance improvements in Dynamo 0.4, see 
Dynamo 0.4 Delivers 4x Faster Performance, SLO-Based Autoscaling, and Real-Time Observability
.

In addition to traditional checkpointing and load-balancing fault mitigation techniques, NCCL communicators can be dynamically resized after a fault allowing recovery within the application without fully restarting the workload.

Popular methods for deploying inference workloads (such as Kubernetes) already provide mechanisms for re-launching replacement workers, but the application must also initiate fault-mitigation steps for the NCCL communicator as well. Recovering from a fault contained to a subset of ranks is similar to a scale-down procedure in which the ranks are removed from the communicator.

The difference is that even healthy ranks should expect NCCL to either return an error or hang on any collective operation. Typical recovery for the healthy ranks starts with 
ncclCommAbort
 on the existing communicator, followed by 
ncclCommInit
 to form a new communicator with the surviving ranks.

 

 
Figure 2. Faulted workers prevent inference from being completed. Fault mitigation removes the workers, and allows the healthy workers to continue accepting requests

NCCL 2.27
 introduced 
ncclCommShrink
, which is an optimization and simplification to this recovery process. When passed the 
NCCL_SHRINK_ABORT
 flag and a list of which ranks to exclude, 
ncclCommShrink
 cancels any hung operations, and creates a new communicator without the need to call 
ncclGetUniqueId
 or 
ncclCommInit
.

Dynamic-scaling and fault-tolerant application example

Using these concepts, you can build a simple example of a NCCL application which can respond to scaling requests from the framework:

#include <stdio.h>
#include <unistd.h>
#include <string>
#include <chrono>
#include <cstdlib>
#include <stdexcept>
#include <vector>

#include "nccl.h"

/* the various kinds of scaling this example supports: */
enum scalingRequestType { NONE, SCALING_NORMAL, SCALING_ABORT, SHRINK_NORMAL, SHRINK_ABORT };

/* Framework Functions: The specific details are not important, so
implementation is not included.*/
void frameworkGetInferenceWork(void **queries, enum scalingRequestType *scaling);
void frameworkNotifyTimeout();
void frameworkNotifyError();
void frameworkDetermineNewRank(int *rank, int *count);
void frameworkGetUniqueId(ncclUniqueId *uid);
void frameworkPutUniqueId(ncclUniqueId uid);
void frameworkGetExcludedRanks(std::vector<int> *excluded);
void exitAbort();
void exitCleanly();

/* Example placeholder function for main job of this worker. Assumes the need
to use a communicator to coordinate work across workers. */
void executePrefillAndDecode(ncclComm_t comm, void *queries);

/* forward declarations of scaleCommunicator and shrinkCommunicator which are
implemented below. These replace the comm with a new, resized communicator. */
void scaleCommunicator(ncclComm_t *comm, enum scalingRequestType *scaling);
void shrinkCommunicator(ncclComm_t *comm, enum scalingRequestType *scaling);

/* In this example, use C++ exception handling to exit from
executePrefillAndDecode so that the framework may react to an error. Use
multiple kinds of exceptions to separate various classes of errors. */
struct AppException : public std::runtime_error {
 AppException(const std::string& message): std::runtime_error(message) {}
};
struct AppNCCLTimeoutException : public AppException {
 AppNCCLTimeoutException(const std::string& message): AppException(message) {}
};
struct AppNCCLErrorException : public AppException {
 AppNCCLErrorException(const std::string& message): AppException(message) {}
};

/* We use a custom NCCL_CHECK macro which raises a C++ exception unless the
operation returns ncclSuccess or ncclInProgress */
#define NCCL_CHECK(call) do { \
 ncclResult_t result = call; \
 if (result != ncclSuccess && result != ncclInProgress) { \
 printf("NCCL error: %s at %s:%d\n", ncclGetErrorString(result), __FILE__, __LINE__); \
 AppNCCLErrorException("NCCL Error"); \
 } \
} while (0)

/* Define a custom NCCL_WAIT macro, which will wait for some fixed amount of
time before assuming something is wrong. */
#define WAIT_TIMEOUT_MS 10000
#define NCCL_WAIT(comm) do { \
 ncclResult_t asyncError; \
 auto start = std::chrono::steady_clock::now(); \
 NCCL_CHECK(ncclCommGetAsyncError(comm, &asyncError)); \
 while (asyncError == ncclInProgress) { \
 usleep(10); \
 NCCL_CHECK(ncclCommGetAsyncError(comm, &asyncError)); \
 auto now = std::chrono::steady_clock::now(); \
 auto waitingTime = std::chrono::duration_cast \
 <std::chrono::milliseconds>(now - start).count(); \
 if (WAIT_TIMEOUT_MS > waitingTime ) { \
 throw AppNCCLTimeoutException("NCCL Timeout"); \
 } \
 } \
 NCCL_CHECK(asyncError); \
} while (0)

/* Use ncclCommInitRankConfig to create a new communicator to replace the old
 one. Optionally call ncclCommAbort. */
void scaleCommunicator(ncclComm_t *comm, int scalingFlag) {

 int rank, rankCount;
 ncclComm_t oldComm = *comm;
 ncclComm_t newComm = NULL;
 if (scalingFlag == SCALING_ABORT) {
 /* The framework has indicated there was an error. ncclCommAbort will exit
 any operation currently in progress, and destroy the communicator. */
 NCCL_CHECK(ncclCommAbort(oldComm));
 NCCL_WAIT(oldComm);
 } else {
 /* Normal condition: simply clean up the old communicator before creating a
 new one.*/
 NCCL_CHECK(ncclCommDestroy(oldComm));
 }

 /* enable non-blocking NCCL communicator so that we may detect and react to
 timeouts. */
 ncclConfig_t config = NCCL_CONFIG_INITIALIZER;
 ncclUniqueId uniqueId;
 config.blocking = 0;

 /* ask the framework what rank we are to be assigned in the new communicator,
 and how many ranks there will be total. These are required inputs to
 ncclCommInit.*/
 frameworkDetermineNewRank(&rank, &rankCount);
 if (rank == 0) {
 /* This worker is special: it will generate the ncclUniqueId, and share it
 with other ranks. */
 ncclGetUniqueId(&uniqueId);
 frameworkPutUniqueId(uniqueId);
 } else if (rank > 0) {
 frameworkGetUniqueId(&uniqueId);
 } else if (rank < 0) {
 /* special value for scale-down: this rank is being removed and should
 exit. */
 exitCleanly();
 }

 /* perform NCCL communicator initialization, and since it is a non-blocking
 communicator, wait until the operation completes. */
 NCCL_CHECK(ncclCommInitRankConfig(&newComm, rankCount, uniqueId, rank, &config));
 NCCL_WAIT(newComm);
 *comm = newComm;
}

/* shrinkCommunicator: Use ncclCommShrink as a simplified and optimized option
when scaling down. */
void shrinkCommunicator(ncclComm_t *comm, int scalingFlag) {

 ncclComm_t oldComm = *comm;

 int ncclShrinkOption;
 bool exiting = false;
 ncclConfig_t config = NCCL_CONFIG_INITIALIZER;
 config.blocking = 0;
 ncclComm_t newComm;
 std::vector<int> excluded;

 /* query the framework for which ranks will be excluded in the new
 communicator. */
 frameworkGetExcludedRanks(&excluded);
 int oldRank;
 NCCL_CHECK(ncclCommUserRank( oldComm, &oldRank) );
 for (int i=0; i<(int)excluded.size(); i++) {
 if (oldRank == excluded[i]) {
 exiting = true;
 }
 }

 ncclShrinkOption = scalingFlag == SHRINK_ABORT ? NCCL_SHRINK_ABORT : NCCL_SHRINK_DEFAULT;
 if (!exiting) {
 /* execute the shrink operation. After executing, wait on the old
 communicator for success, and finally assign *comm to be the new communicator.
 */
 NCCL_CHECK(ncclCommShrink(oldComm, excluded.data(), excluded.size(), \
 &newComm, &config, ncclShrinkOption));
 NCCL_WAIT(oldComm);
 NCCL_WAIT(newComm);
 *comm = newComm;
 }
 if (ncclShrinkOption == NCCL_SHRINK_ABORT) {
 ncclCommAbort(oldComm);
 } else {
 ncclCommDestroy(oldComm);
 }
 if (exiting) { exitCleanly(); }
}

/* persistent state between mainLoop iterations */
ncclComm_t comm = NULL;
void *queries = NULL;

/* mainLoop: called repeatedly during the life of this worker. */
void mainLoop() {
 enum scalingRequestType scalingFlag;

 /* The framework provides the workers with some work to do (queries) and
 signals any scaling actions that should happen. The framework will ensure all
 workers observe the same value for scalingFlag during each pass through the
 mainloop.
 */
 frameworkGetInferenceWork(&queries, &scalingFlag);

 /* Act on the scalingFlag: */
 if (scalingFlag == SCALING_NORMAL || scalingFlag == SCALING_ABORT) {
 scaleCommunicator(&comm, scalingFlag);
 } else if (scalingFlag == SHRINK_NORMAL || scalingFlag == SHRINK_ABORT) {
 shrinkCommunicator(&comm, scalingFlag);
 }

 /* Perform inference work. Catch any exceptions raised and communicate any
 problems to the framework. */
 try {
 executePrefillAndDecode(comm, queries);
 } catch (const AppNCCLTimeoutException &e) {
 frameworkNotifyTimeout();
 } catch (const AppNCCLErrorException &e) {
 frameworkNotifyError();
 }
}

This example is modeled on a distributed inference application and demonstrates how a framework can direct workers to perform scale-up or scale-down operations. The core logic is captured in two key functions: 
scaleCommunicator
 and 
shrinkCommunicator
. These are invoked by the framework as needed. The primary inference work is handled by 
executePrefillAndDecode
, which uses an active communicator that can be replaced over the worker’s lifetime.

The application is built around a central mainLoop that represents the continuous work of an inference worker. On each iteration, the worker gets new tasks from the framework and checks for a 
scalingFlag
 that signals if a resizing operation should occur. The framework ensures that these scaling requests are delivered synchronously to all workers. In the event of a fault, a worker will either time out or receive an error from NCCL. In either scenario, the exception handling path notifies the framework, prompting a fault recovery to begin.

Coordinated actions among workers require a central monitoring component, which we can call an Application Monitor. This component is typically responsible for tracking worker health, traffic load, and request latency. Based on these metrics, the Application Monitor signals the workers when to scale the pool up or down.

To handle increased traffic, for example, the Application Monitor identifies available GPUs, launches new worker processes, and then sets the scaling flag to signal the existing workers to expand the communicator. The 
scaleCommunicator
 function manages this process, where workers coordinate to establish the new communicator size and share the required 
ncclUniqueId
.

Conversely, when traffic subsides, the Application Monitor signals a scale-down, identifying which ranks should be removed. For this specific case, the 
shrinkCommunicator
 function provides an optimized path using 
ncclCommShrink
, a simplified interface that does not require generating and distributing a new 
ncclUniqueId
. Once ranks exit, their underlying GPU resources can be released back to the cluster’s allocation system or cloud provider.

Finally, both 
scaleCommunicator
 and 
shrinkCommunicator
 are equipped to handle fault recovery. Once the Application Monitor identifies a faulted component, it can direct the healthy workers to remove it by invoking the Abort path of either function. These paths take extra steps—calling 
ncclCommAbort
 or setting the 
NCCL_SHRINK_ABORT
 flag—to ensure that the active communicator does not hang while waiting for a peer that has failed.

Get started with scalable and fault-tolerant NCCL applications

NCCL support for dynamic communicators provides a powerful tool for building modern, resilient AI infrastructure. By moving beyond a static, launch-time configuration, you can create applications that adapt to changing workloads and can be optimized for efficiency and cost. 

In addition, with the ability to call 
ncclCommAbort
 or 
ncclCommShrink
, handling unexpected hardware or software faults is possible without a full abort and restart. Build your next multi-GPU application with these dynamic capabilities to create a scalable and fault-tolerant system. Download the 
latest NCCL releas
e or use a pre-built container, such as the 
PyTorch NGC Container
.

 

 

 

 
 Discuss (0)
 

 

 
 

 
 
 

 
 

 Like

 

 

 

 

 
Tags

 

 

 
Data Center / Cloud
 | 
Developer Tools & Techniques
 | 
MLOps
 | 
Networking / Communications
 | 
General
 | 
DOCA
 | 
NCCL
 | 
Intermediate Technical
 | 
Tutorial
 | 
AI Inference
 | 
featured
 

 

 

 

 

 

 About the Authors
 

 

 

 

 

 

 

 

 About Luke Robison
 

 

 
 Luke Robison is an NVIDIA Collective Communications Library (NCCL) developer focusing on improving AI/ML speed and resiliency with the latest hardware capabilities. He started at NVIDIA in the summer of 2025 after taking over 15 years to random-walk through the fields of sonar systems, HPC applications, and high-speed networking while constantly over-indexing on software optimization. After graduating from The University of Texas in 2008, Luke has called Austin his permanent home, but enjoys traveling the world with his family.
 
 
 

 

 View all posts by Luke Robison

 

 

 

 

 

 

 

 

 

 

 About Jim Dinan
 

 

 
 Jim Dinan is a distinguished engineer at NVIDIA and leads the GPU Communications Software Architecture team. Jim was a James Wallace Givens postdoctoral fellow at Argonne National Laboratory and earned a Ph.D. in Computer Science from the Ohio State University. Jim’s work focuses on hardware/software codesign, high-speed networking, and scalable communications software.
 
 
 

 

 View all posts by Jim Dinan

 

 

 

 

 

 

 

 

 

 

 About Misbah Mubarak
 

 

 
 Misbah Mubarak is a distinguished software engineer in the GPU software team at Nvidia. She has over 10 years of experience in large-scale, high-performance & distributed computing; network technologies; and the design of cloud network fabrics.
 
 
 

 

 View all posts by Misbah Mubarak

 

 

 

 

 

 

 

 

 

 

 
Comments
