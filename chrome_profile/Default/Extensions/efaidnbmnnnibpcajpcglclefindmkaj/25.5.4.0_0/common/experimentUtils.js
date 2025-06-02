/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
import{EXPERIMENT_VARIANTS_STORAGE_KEY as t}from"../sw_modules/constant.js";import{dcLocalStorage as e}from"./local-storage.js";function r(){const r=e.getItem(t);return(Array.isArray(r)?r.sort():[]).join("_")}function o(r){if(!r)return;let o=e.getItem(t)||[];o.includes(r)||o.push(r),e.setItem(t,o)}function n(r){let o=e.getItem(t)||[];o.includes(r)&&(o=o.filter((t=>t!==r))),e.setItem(t,o)}export{r as getActiveExperimentAnalyticsString,o as setExperimentCodeForAnalytics,n as removeExperimentCodeForAnalytics};