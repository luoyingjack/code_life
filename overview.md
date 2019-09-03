## Overview

**All data is sent and received as JSON.**

**Success Response**

    HTTP/1.1 200 OK
    {
        code: 0,
        message: "Success",
        data: {
            <响应数据>
        }
    }

**Error Response**

    HTTP/1.1 200 OK
    {
        code: <错误码>,
        message: <错误描述>,
        data: {}
    }

**General Code & Message**

    1000: "Internal Server Error"
    1100: "Bad Request"
    1101: "Unauthorized"
