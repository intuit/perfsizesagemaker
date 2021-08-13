var stats = {
    type: "GROUP",
name: "Global Information",
path: "",
pathFormatted: "group_missing-name-b06d1",
stats: {
    "name": "Global Information",
    "numberOfRequests": {
        "total": "36000",
        "ok": "35998",
        "ko": "2"
    },
    "minResponseTime": {
        "total": "7",
        "ok": "7",
        "ko": "7"
    },
    "maxResponseTime": {
        "total": "1044",
        "ok": "1044",
        "ko": "743"
    },
    "meanResponseTime": {
        "total": "11",
        "ok": "11",
        "ko": "375"
    },
    "standardDeviation": {
        "total": "17",
        "ok": "17",
        "ko": "368"
    },
    "percentiles1": {
        "total": "10",
        "ok": "10",
        "ko": "375"
    },
    "percentiles2": {
        "total": "12",
        "ok": "12",
        "ko": "559"
    },
    "percentiles3": {
        "total": "15",
        "ok": "15",
        "ko": "706"
    },
    "percentiles4": {
        "total": "22",
        "ok": "22",
        "ko": "736"
    },
    "group1": {
        "name": "t < 800 ms",
        "count": 35990,
        "percentage": 100
    },
    "group2": {
        "name": "800 ms < t < 1200 ms",
        "count": 8,
        "percentage": 0
    },
    "group3": {
        "name": "t > 1200 ms",
        "count": 0,
        "percentage": 0
    },
    "group4": {
        "name": "failed",
        "count": 2,
        "percentage": 0
    },
    "meanNumberOfRequestsPerSecond": {
        "total": "198.895",
        "ok": "198.884",
        "ko": "0.011"
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
        "total": "36000",
        "ok": "35998",
        "ko": "2"
    },
    "minResponseTime": {
        "total": "7",
        "ok": "7",
        "ko": "7"
    },
    "maxResponseTime": {
        "total": "1044",
        "ok": "1044",
        "ko": "743"
    },
    "meanResponseTime": {
        "total": "11",
        "ok": "11",
        "ko": "375"
    },
    "standardDeviation": {
        "total": "17",
        "ok": "17",
        "ko": "368"
    },
    "percentiles1": {
        "total": "10",
        "ok": "10",
        "ko": "375"
    },
    "percentiles2": {
        "total": "12",
        "ok": "12",
        "ko": "559"
    },
    "percentiles3": {
        "total": "15",
        "ok": "15",
        "ko": "706"
    },
    "percentiles4": {
        "total": "22",
        "ok": "22",
        "ko": "736"
    },
    "group1": {
        "name": "t < 800 ms",
        "count": 35990,
        "percentage": 100
    },
    "group2": {
        "name": "800 ms < t < 1200 ms",
        "count": 8,
        "percentage": 0
    },
    "group3": {
        "name": "t > 1200 ms",
        "count": 0,
        "percentage": 0
    },
    "group4": {
        "name": "failed",
        "count": 2,
        "percentage": 0
    },
    "meanNumberOfRequestsPerSecond": {
        "total": "198.895",
        "ok": "198.884",
        "ko": "0.011"
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
