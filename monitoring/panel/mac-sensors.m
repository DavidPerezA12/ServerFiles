// Prints one JSON object with this Mac's real sensor readings (no root needed):
//   temps:   every HID temperature sensor, by macOS's own name (°C)
//   fan:     SMC fan 0 actual / minimum / maximum RPM
//   fans:    the same reading for every fan the SMC reports (F0, F1, ...)
//   thermal: macOS thermal state (0 nominal, 1 fair, 2 serious, 3 critical)
// Build: clang -O2 -fobjc-arc -framework Foundation -framework IOKit mac-sensors.m -o mac-sensors
#import <Foundation/Foundation.h>
#import <IOKit/IOKitLib.h>
#import <IOKit/hidsystem/IOHIDEventSystemClient.h>

typedef struct __IOHIDEvent *IOHIDEventRef;
typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
extern IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef);
extern int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef, CFDictionaryRef);
extern CFArrayRef IOHIDEventSystemClientCopyServices(IOHIDEventSystemClientRef);
extern CFTypeRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef, CFStringRef);
extern IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
extern double IOHIDEventGetFloatValue(IOHIDEventRef, int32_t);
#define kTemperatureEvent 15

typedef struct { char major, minor, build, reserved; UInt16 release; } SMCVers;
typedef struct { UInt16 version, length; UInt32 cpu, gpu, mem; } SMCLimit;
typedef struct { UInt32 dataSize, dataType; char attributes; } SMCKeyInfo;
typedef struct { UInt32 key; SMCVers vers; SMCLimit limit; SMCKeyInfo info; char result, status, data8; UInt32 data32; unsigned char bytes[32]; } SMCData;

static io_connect_t smc;
static int smcCall(SMCData *in, SMCData *out) { size_t size = sizeof(SMCData); return IOConnectCallStructMethod(smc, 2, in, sizeof(SMCData), out, &size); }
static NSNumber *smcFloat(const char *name) {
    UInt32 key = (name[0] << 24) | (name[1] << 16) | (name[2] << 8) | name[3];
    SMCData in = {0}, out = {0};
    in.key = key; in.data8 = 9;                       // read key info
    if (smcCall(&in, &out) || out.result || out.info.dataSize != 4 || out.info.dataType != 'flt ') return nil;
    SMCKeyInfo info = out.info;
    memset(&in, 0, sizeof in); memset(&out, 0, sizeof out);
    in.key = key; in.info = info; in.data8 = 5;       // read bytes
    if (smcCall(&in, &out) || out.result) return nil;
    float value; memcpy(&value, out.bytes, 4);
    return @(round(value));
}

int main(void) {
    @autoreleasepool {
        NSMutableDictionary *temps = [NSMutableDictionary dictionary];
        IOHIDEventSystemClientRef client = IOHIDEventSystemClientCreate(kCFAllocatorDefault);
        IOHIDEventSystemClientSetMatching(client, (__bridge CFDictionaryRef)@{@"PrimaryUsagePage": @0xff00, @"PrimaryUsage": @5});
        NSArray *services = CFBridgingRelease(IOHIDEventSystemClientCopyServices(client));
        for (id service in services) {
            IOHIDServiceClientRef ref = (__bridge IOHIDServiceClientRef)service;
            NSString *name = CFBridgingRelease(IOHIDServiceClientCopyProperty(ref, CFSTR("Product")));
            IOHIDEventRef event = IOHIDServiceClientCopyEvent(ref, kTemperatureEvent, 0, 0);
            if (!name || !event) continue;
            double value = IOHIDEventGetFloatValue(event, kTemperatureEvent << 16);
            CFRelease(event);
            temps[name] = @(round(value * 100) / 100);
        }
        CFRelease(client);

        NSMutableArray *fans = [NSMutableArray array];
        io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("AppleSMC"));
        if (service && IOServiceOpen(service, mach_task_self(), 0, &smc) == KERN_SUCCESS) {
            // Fans are numbered from 0; the first missing actual-RPM key ends the list.
            for (int i = 0; i < 4; i++) {
                NSMutableDictionary *fan = [NSMutableDictionary dictionary];
                NSDictionary *keys = @{@"rpm": @"F%dAc", @"min": @"F%dMn", @"max": @"F%dMx"};
                for (NSString *field in keys) {
                    NSNumber *value = smcFloat([[NSString stringWithFormat:keys[field], i] UTF8String]);
                    if (value) fan[field] = value;
                }
                if (!fan[@"rpm"]) break;
                [fans addObject:fan];
            }
            IOServiceClose(smc);
        }
        if (service) IOObjectRelease(service);

        NSDictionary *result = @{@"temps": temps, @"fan": fans.count ? fans[0] : @{}, @"fans": fans,
                                 @"thermal": @(NSProcessInfo.processInfo.thermalState)};
        NSData *json = [NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingSortedKeys error:nil];
        fwrite(json.bytes, 1, json.length, stdout);
        fputc('\n', stdout);
    }
    return 0;
}
