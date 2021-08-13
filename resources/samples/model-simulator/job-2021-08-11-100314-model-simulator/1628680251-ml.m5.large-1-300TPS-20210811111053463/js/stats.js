var stats = {
    type: "GROUP",
name: "Global Information",
path: "",
pathFormatted: "group_missing-name-b06d1",
stats: {
    "name": "Global Information",
    "numberOfRequests": {
        "total": "54000",
        "ok": "53978",
        "ko": "22"
    },
    "minResponseTime": {
        "total": "6",
        "ok": "7",
        "ko": "6"
    },
    "maxResponseTime": {
        "total": "10042",
        "ok": "10042",
        "ko": "106"
    },
    "meanResponseTime": {
        "total": "15",
        "ok": "15",
        "ko": "12"
    },
    "standardDeviation": {
        "total": "156",
        "ok": "156",
        "ko": "21"
    },
    "percentiles1": {
        "total": "11",
        "ok": "11",
        "ko": "7"
    },
    "percentiles2": {
        "total": "13",
        "ok": "13",
        "ko": "9"
    },
    "percentiles3": {
        "total": "17",
        "ok": "17",
        "ko": "16"
    },
    "percentiles4": {
        "total": "44",
        "ok": "44",
        "ko": "87"
    },
    "group1": {
        "name": "t < 800 ms",
        "count": 53944,
        "percentage": 100
    },
    "group2": {
        "name": "800 ms < t < 1200 ms",
        "count": 16,
        "percentage": 0
    },
    "group3": {
        "name": "t > 1200 ms",
        "count": 18,
        "percentage": 0
    },
    "group4": {
        "name": "failed",
        "count": 22,
        "percentage": 0
    },
    "meanNumberOfRequestsPerSecond": {
        "total": "285.714",
        "ok": "285.598",
        "ko": "0.116"
    }
},
contents: {
"req_sagemaker-learn-6e012": {
        type: "REQUEST",
        name: "SageMaker-LEARNING-model-simulator-1",
path: "SageMaker-LEARNING-model-simulator-1",
pathFormatted: "req_sagemaker-learn-6e012",
stats: {
    "name": "SageMaker-LEARNING-model-simulator-1",
    "numberOfRequests": {
        "total": "54000",
        "ok": "53978",
        "ko": "22"
    },
    "minResponseTime": {
        "total": "6",
        "ok": "7",
        "ko": "6"
    },
    "maxResponseTime": {
        "total": "10042",
        "ok": "10042",
        "ko": "106"
    },
    "meanResponseTime": {
        "total": "15",
        "ok": "15",
        "ko": "12"
    },
    "standardDeviation": {
        "total": "156",
        "ok": "156",
        "ko": "21"
    },
    "percentiles1": {
        "total": "11",
        "ok": "11",
        "ko": "7"
    },
    "percentiles2": {
        "total": "13",
        "ok": "13",
        "ko": "9"
    },
    "percentiles3": {
        "total": "17",
        "ok": "17",
        "ko": "16"
    },
    "percentiles4": {
        "total": "44",
        "ok": "44",
        "ko": "87"
    },
    "group1": {
        "name": "t < 800 ms",
        "count": 53944,
        "percentage": 100
    },
    "group2": {
        "name": "800 ms < t < 1200 ms",
        "count": 16,
        "percentage": 0
    },
    "group3": {
        "name": "t > 1200 ms",
        "count": 18,
        "percentage": 0
    },
    "group4": {
        "name": "failed",
        "count": 22,
        "percentage": 0
    },
    "meanNumberOfRequestsPerSecond": {
        "total": "285.714",
        "ok": "285.598",
        "ko": "0.116"
    }
}
    }
}

}

function fillStats(stat){
    $("#numberOfRequests").append(stat.numberOfRequests.total);
    $("#numberOfRequestsOK").append(stat.numberOfRequests.ok);
    $("#numberOfRequestsKO").append(stat.numberOfRequests.ko);

    $("#minResponseTime").append(stat.minResponseTime.total);
    $("#minResponseTimeOK").append(stat.minResponseTime.ok);
    $("#minResponseTimeKO").append(stat.minResponseTime.ko);

    $("#maxResponseTime").append(stat.maxResponseTime.total);
    $("#maxResponseTimeOK").append(stat.maxResponseTime.ok);
    $("#maxResponseTimeKO").append(stat.maxResponseTime.ko);

    $("#meanResponseTime").append(stat.meanResponseTime.total);
    $("#meanResponseTimeOK").append(stat.meanResponseTime.ok);
    $("#meanResponseTimeKO").append(stat.meanResponseTime.ko);

    $("#standardDeviation").append(stat.standardDeviation.total);
    $("#standardDeviationOK").append(stat.standardDeviation.ok);
    $("#standardDeviationKO").append(stat.standardDeviation.ko);

    $("#percentiles1").append(stat.percentiles1.total);
    $("#percentiles1OK").append(stat.percentiles1.ok);
    $("#percentiles1KO").append(stat.percentiles1.ko);

    $("#percentiles2").append(stat.percentiles2.total);
    $("#percentiles2OK").append(stat.percentiles2.ok);
    $("#percentiles2KO").append(stat.percentiles2.ko);

    $("#percentiles3").append(stat.percentiles3.total);
    $("#percentiles3OK").append(stat.percentiles3.ok);
    $("#percentiles3KO").append(stat.percentiles3.ko);

    $("#percentiles4").append(stat.percentiles4.total);
    $("#percentiles4OK").append(stat.percentiles4.ok);
    $("#percentiles4KO").append(stat.percentiles4.ko);

    $("#meanNumberOfRequestsPerSecond").append(stat.meanNumberOfRequestsPerSecond.total);
    $("#meanNumberOfRequestsPerSecondOK").append(stat.meanNumberOfRequestsPerSecond.ok);
    $("#meanNumberOfRequestsPerSecondKO").append(stat.meanNumberOfRequestsPerSecond.ko);
}
