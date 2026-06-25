---
type: RawSource
title: https://docs.nvidia.com/deeplearning/nccl/release-notes/rel_2-4-2.html
source_kind: web
url: https://docs.nvidia.com/deeplearning/nccl/release-notes/rel_2-4-2.html
captured: 2026-06-24
status: ingested
---
# Snapshot

URL: https://docs.nvidia.com/deeplearning/nccl/release-notes/rel_2-4-2.html

Content-Type: text/html

<!DOCTYPE html
  PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en-us" xml:lang="en-us">
   <head>
      <!-- OneTrust Cookies Consent Notice start for nvidia.com -->
      <script src="https://cdn.cookielaw.org/scripttemplates/otSDKStub.js" data-document-language="true" type="text/javascript" charset="UTF-8" data-domain-script="3e2b62ff-7ae7-4ac5-87c8-d5949ecafff5"></script>
      <script type="text/javascript">
        function OptanonWrapper() { };
      </script>
      <!-- OneTrust Cookies Consent Notice end for nvidia.com -->
      <!-- OneTrust gpc signal detection script start -->
      <script type="text/javascript"> 
        (function () {
          "use strict";
          const observer = new MutationObserver(function (mutations, mutationInstance) {
            const otPreferencePanel = document.getElementById('onetrust-pc-sdk');
            if (otPreferencePanel) {
              const otBanner = document.getElementById('onetrust-banner-sdk');
              if (otBanner && navigator.globalPrivacyControl) {
                setNvDone();
              }
              mutationInstance.disconnect();
            }
          });
          observer.observe(document, {
            childList: true,
            subtree: true
          });
  
          const setNvDone = function () {
            // Hide elements by their IDs
            var acceptbtn = document.getElementById('onetrust-accept-btn-handler');
            var rejectbtn = document.getElementById('onetrust-reject-all-handler');
            if (acceptbtn) {
              acceptbtn.style.display = 'none';
            }
            if (rejectbtn) {
              rejectbtn.style.display = 'none';
            }
            const doneButton = document.createElement('button');
            doneButton.id = 'nv-done-btn-handler';
            doneButton.textContent = 'Done';
  
            document.getElementById('onetrust-button-group').appendChild(doneButton);
  
            // Add click event listener to the new button
            doneButton.addEventListener('click', function () {
              OneTrust.Close();
            });
          };
        })();
      </script>
      <!-- OneTrust gpc signal detection script end -->
      <meta http-equiv="Content-Type" content="text/html; charset=utf-8"></meta>
      <meta http-equiv="X-UA-Compatible" content="IE=edge"></meta>
      <meta name="copyright" content="(C) Copyright 2005"></meta>
      <meta name="DC.rights.owner" content="(C) Copyright 2005"></meta>
      <meta name="DC.Type" content="reference"></meta>
      <meta name="DC.Title" content="NCCL Release 2.4.2"></meta>
      <meta name="abstract" content=""></meta>
      <meta name="description" content=""></meta>
      <meta name="DC.Format" content="XHTML"></meta>
      <meta name="DC.Identifier" content="rel_2-4-2"></meta>
      <link rel="stylesheet" type="text/css" href="../common/formatting/commonltr.css"></link>
      <link rel="stylesheet" type="text/css" href="../common/formatting/site.css"></link>
      <title>Release Notes :: NVIDIA Deep Learning NCCL Documentation</title>
      <link rel="stylesheet" type="text/css" href="../common/formatting/qwcode.highlight.css"></link>
      <!--[if lt IE 9]>
      <script src="../common/formatting/html5shiv-printshiv.min.js"></script>
      <![endif]-->
      <script src="//assets.adobedtm.com/5d4962a43b79/c1061d2c5e7b/launch-191c2462b890.min.js"></script>
      <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-svg.min.js"></script>
      <script type="text/javascript" charset="utf-8" src="../common/formatting/jquery.min.js"></script>
      <script type="text/javascript" charset="utf-8" src="../common/formatting/jquery.ba-hashchange.min.js"></script>
      <script type="text/javascript" charset="utf-8" src="../common/formatting/jquery.scrollintoview.min.js"></script>
      <script type="text/javascript" src="../search/htmlFileList.js"></script>
      <script type="text/javascript" src="../search/htmlFileInfoList.js"></script>
      <script type="text/javascript" src="../search/nwSearchFnt.min.js"></script>
      <script type="text/javascript" src="../search/stemmers/en_stemmer.min.js"></script>
      <script type="text/javascript" src="../search/index-1.js"></script>
      <script type="text/javascript" src="../search/index-2.js"></script>
      <script type="text/javascript" src="../search/index-3.js"></script>
      <link rel="canonical" href="http://docs.nvidia.com/deeplearning/nccl/release-notes/index.html"></link>
   </head>
   <body>
      
      <header id="header"><span id="company">NVIDIA</span><span id="site-title">NVIDIA Deep Learning NCCL Documentation</span><form id="search" method="get" action="search">
            <input type="text" name="search-text"></input><fieldset id="search-location">
               <legend>Search In:</legend>
               <label><input type="radio" name="search-type" value="site"></input>Entire Site</label>
               <label><input type="radio" name="search-type" value="document"></input>Just This Document</label></fieldset>
            <button type="reset">clear search</button>
            <button id="submit" type="submit">search</button></form>
      </header>
      <div id="site-content">
         <nav id="site-nav">
            <div class="category closed"><a href="../index.html" title="The root of the site.">Getting Started</a></div>
            <div class="category"><a href="index.html" title="Release Notes">Release Notes</a></div>
            <ul>
               <li>
                  <div class="section-link"><a href="overview.html#overview">1.&nbsp;NCCL Overview</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-30-7.html#rel_2-30-7">2.&nbsp;NCCL Release 2.30.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-30-4.html#rel_2-30-4">3.&nbsp;NCCL Release 2.30.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-30-3.html#rel_2-30-3">4.&nbsp;NCCL Release 2.30.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-29-7.html#rel_2-29-7">5.&nbsp;NCCL Release 2.29.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-29-3.html#rel_2-29-3">6.&nbsp;NCCL Release 2.29.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-29-2.html#rel_2-29-2">7.&nbsp;NCCL Release 2.29.2</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-28-9.html#rel_2-28-9">8.&nbsp;NCCL Release 2.28.9</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-28-7.html#rel_2-28-7">9.&nbsp;NCCL Release 2.28.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-28-3.html#rel_2-28-3">10.&nbsp;NCCL Release 2.28.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-27-7.html#rel_2-27-7">11.&nbsp;NCCL Release 2.27.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-27-6.html#rel_2-27-6">12.&nbsp;NCCL Release 2.27.6</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-27-5.html#rel_2-27-5">13.&nbsp;NCCL Release 2.27.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-27-3.html#rel_2-27-3">14.&nbsp;NCCL Release 2.27.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-26-5.html#rel_2-26-5">15.&nbsp;NCCL Release 2.26.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-26-2.html#rel_2-26-2">16.&nbsp;NCCL Release 2.26.2</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-25-1.html#rel_2-25-1">17.&nbsp;NCCL Release 2.25.1</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-24-3.html#rel_2-24-3">18.&nbsp;NCCL Release 2.24.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-23-4.html#rel_2-23-4">19.&nbsp;NCCL Release 2.23.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-22-3.html#rel_2-22-3">20.&nbsp;NCCL Release 2.22.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-21-5.html#rel_2-21-5">21.&nbsp;NCCL Release 2.21.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-20-5.html#rel_2-20-5">22.&nbsp;NCCL Release 2.20.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-20-3.html#rel_2-20-3">23.&nbsp;NCCL Release 2.20.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-19-3.html#rel_2-19-3">24.&nbsp;NCCL Release 2.19.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-18-5.html#rel_2-18-5">25.&nbsp;NCCL Release 2.18.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-18-3.html#rel_2-18-3">26.&nbsp;NCCL Release 2.18.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-18-1.html#rel_2-18-1">27.&nbsp;NCCL Release 2.18.1</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-17-1.html#rel_2-17-1">28.&nbsp;NCCL Release 2.17.1</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-16-5.html#rel_2-16-5">29.&nbsp;NCCL Release 2.16.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-16-2.html#rel_2-16-2">30.&nbsp;NCCL Release 2.16.2</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-15-5.html#rel_2-15-5">31.&nbsp;NCCL Release 2.15.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-15-1.html#rel_2-15-1">32.&nbsp;NCCL Release 2.15.1</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-14-3.html#rel_2-14-3">33.&nbsp;NCCL Release 2.14.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-13-4.html#rel_2-13-4">34.&nbsp;NCCL Release 2.13.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-12-12.html#rel_2-12-12">35.&nbsp;NCCL Release 2.12.12</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-12-10.html#rel_2-12-10">36.&nbsp;NCCL Release 2.12.10</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-12-7.html#rel_2-12-7">37.&nbsp;NCCL Release 2.12.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-11-4.html#rel_2-11-4">38.&nbsp;NCCL Release 2.11.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-10-3.html#rel_2-10-3">39.&nbsp;NCCL Release 2.10.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-9-9.html#rel_2-9-9">40.&nbsp;NCCL Release 2.9.9</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-9-8.html#rel_2-9-8">41.&nbsp;NCCL Release 2.9.8</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-9-6.html#rel_2-9-6">42.&nbsp;NCCL Release 2.9.6</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-8-4.html#rel_2-8-4">43.&nbsp;NCCL Release 2.8.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-8-3.html#rel_2-8-3">44.&nbsp;NCCL Release 2.8.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-7-8.html#rel_2-7-8">45.&nbsp;NCCL Release 2.7.8</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-7-6.html#rel_2-7-6">46.&nbsp;NCCL Release 2.7.6</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-7-5.html#rel_2-7-5">47.&nbsp;NCCL Release 2.7.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-7-3.html#rel_2-7-3">48.&nbsp;NCCL Release 2.7.3</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-6-4.html#rel_2-6-4">49.&nbsp;NCCL Release 2.6.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-5-6.html#rel_2-5-6">50.&nbsp;NCCL Release 2.5.6</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-4-8.html#rel_2-4-8">51.&nbsp;NCCL Release 2.4.8</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-4-7.html#rel_2-4-7">52.&nbsp;NCCL Release 2.4.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-4-2.html#rel_2-4-2">53.&nbsp;NCCL Release 2.4.2</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-3-7.html#rel_2-3-7">54.&nbsp;NCCL Release 2.3.7</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-3-5.html#rel_2-3-5">55.&nbsp;NCCL Release 2.3.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-3-4.html#rel_2-3-4">56.&nbsp;NCCL Release 2.3.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-2-13.html#rel_2-2-13">57.&nbsp;NCCL Release 2.2.13</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2-2-12.html#rel_2-2-12">58.&nbsp;NCCL Release 2.2.12</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.1.15.html#rel_2.1.15">59.&nbsp;NCCL Release 2.1.15</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.1.4.html#rel_2.1.4">60.&nbsp;NCCL Release 2.1.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.1.2.html#rel_2.1.2">61.&nbsp;NCCL Release 2.1.2</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.0.5.html#rel_2.0.5">62.&nbsp;NCCL Release 2.0.5</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.0.4.html#rel_2.0.4">63.&nbsp;NCCL Release 2.0.4</a></div>
               </li>
               <li>
                  <div class="section-link"><a href="rel_2.0.2.html#rel_2.0.2">64.&nbsp;NCCL Release 2.0.2</a></div>
               </li>
            </ul>
         </nav>
         <div id="resize-nav"></div>
         <nav id="search-results">
            <h2>Search Results</h2>
            <ol></ol>
         </nav>
         
         <div id="contents-container">
            <div id="breadcrumbs-container">
               <div id="release-info">Release Notes (<a href="../pdf/NCCL-Release-Notes.pdf">PDF</a>)
                  -
                  
                  2.29.2
                  
                  -
                  
                  Last updated June 11, 2026
               </div>
            </div>
            <article id="contents">
               <div class="topic nested0" id="rel_2-4-2"><a name="rel_2-4-2" shape="rect">
                     <!-- --></a><h2 class="title topictitle1"><a href="#rel_2-4-2" name="rel_2-4-2" shape="rect"><span class="ph">NCCL</span> Release 2.4.2</a></h2>
                  <div class="body refbody">
                     <p class="shortdesc"></p>
                     <div class="section">
                        <h2 class="title sectiontitle">Key Features and Enhancements</h2>
                        <div class="p">This NCCL release includes the following key features and enhancements. 
                           <ul class="ul">
                              <li class="li">Implemented tree-based algorithms for better All Reduce performance at scale
                                 and with small and medium size messages.
                              </li>
                              <li class="li">Support for external network plugins (e.g.,
                                 <samp class="ph codeph">libfabric</samp>).
                              </li>
                              <li class="li">Add <samp class="ph codeph">ncclCommGetAsyncError()</samp> function to report errors
                                 happening during collective operations.
                              </li>
                              <li class="li">Add <samp class="ph codeph">ncclCommAbort()</samp> function to destroy a communicator,
                                 aborting any outstanding operations.
                              </li>
                              <li class="li">Support different ranks having a different
                                 <samp class="ph codeph">CUDA_VISIBLE_DEVICES</samp>.
                              </li>
                              <li class="li">Add a best-effort mechanism to check for size mismatch among collective
                                 calls.
                              </li>
                           </ul>
                        </div>
                     </div>
                     <div class="section">
                        <h2 class="title sectiontitle">Fixed Issues</h2>
                        <div class="p">
                           <ul class="ul">
                              <li class="li">Support communication between Mesos containers (Github issue #155).</li>
                              <li class="li">Fix case where <samp class="ph codeph">posix_fallocate()</samp> returns EINTR (Github
                                 issue #137).
                              </li>
                              <li class="li">NCCL threads no longer escape the CPU affinity set by the user or job
                                 scheduler.
                              </li>
                           </ul>
                        </div>
                     </div>
                  </div>
               </div>
               
               
            </article>
            <footer id="footer"><img src="../common/formatting/NVIDIA-LogoBlack.svg"></img><div><a href="https://www.nvidia.com/en-us/about-nvidia/privacy-policy/" target="_blank">Privacy Policy</a> | 
                  <a href="https://www.nvidia.com/en-us/privacy-center/" target="_blank">Manage My Privacy</a> | 
                  <a href="https://www.nvidia.com/en-us/preferences/email-preferences/" target="_blank">Do Not Sell or Share My Data</a> | 
                  <a href="https://www.nvidia.com/en-us/about-nvidia/terms-of-service/" target="_blank">Terms of Service</a> | 
                  <a href="https://www.nvidia.com/en-us/about-nvidia/accessibility/" target="_blank">Accessibility</a> | 
                  <a href="https://www.nvidia.com/en-us/about-nvidia/company-policies/" target="_blank">Corporate Policies</a> | 
                  <a href="https://www.nvidia.com/en-us/product-security/" target="_blank">Product Security</a> | 
                  <a href="https://www.nvidia.com/en-us/contact/" target="_blank">Contact</a></div>
               <div class="copyright">Copyright © 2026 NVIDIA Corporation</div>
            </footer>
         </div>
      </div>
      <script language="JavaScript" type="text/javascript" charset="utf-8" src="../common/formatting/common.min.js"></script>
      <script language="JavaScript" type="text/javascript" charset="utf-8" src="../common/scripts/google-analytics/google-analytics-write.js"></script>
      <script language="JavaScript" type="text/javascript" charset="utf-8" src="../common/scripts/google-analytics/google-analytics-tracker.js"></script>
      <script type="text/javascript">var switchTo5x=true;</script><script type="text/javascript">stLight.options({publisher: "998dc202-a267-4d8e-bce9-14debadb8d92", doNotHash: false, doNotCopy: false, hashAddressBar: false});</script>
      <script type="text/javascript">_satellite.pageBottom();</script></body>
</html>
