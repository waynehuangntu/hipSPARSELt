from hip import hip

def hip_check(call_result):
    print(call_result)
    err = call_result[0]
    result = call_result[1:]
    if len(result) == 1:
        result = result[0]
    if isinstance(err, hip.hipError_t) and err != hip.hipError_t.hipSuccess:
        raise RuntimeError(str(err))
    return result

device_num = 0
device_count = hip_check(hip.hipGetDeviceCount())
print(device_count)

for attrib in (
   hip.hipDeviceAttribute_t.hipDeviceAttributeClockRate,
):
    value = hip_check(hip.hipDeviceGetAttribute(attrib,device_num))
    print(f"{attrib.name}: {value}")
print("ok")