using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;

namespace Receiptly.API.Configuration;

/// <summary>
/// OpenTelemetry configuration for sending telemetry to OTEL Dashboard.
/// </summary>
public static class OpenTelemetryConfiguration
{
    /// <summary>
    /// Configure OpenTelemetry tracing, metrics, and logging.
    /// </summary>
    public static IServiceCollection AddOpenTelemetryConfiguration(
        this IServiceCollection services,
        IConfiguration configuration,
        IWebHostEnvironment environment)
    {
        var serviceName = "Receiptly.API";
        var serviceVersion = "1.0.0";
        var otlpGrpcEndpoint = configuration["OpenTelemetry:OtlpGrpcEndpoint"] ?? "http://localhost:4317";

        // Configure shared resource attributes
        var resourceBuilder = ResourceBuilder.CreateDefault()
            .AddService(serviceName, serviceVersion: serviceVersion)
            .AddAttributes(new Dictionary<string, object>
            {
                ["deployment.environment"] = environment.EnvironmentName,
                ["host.name"] = Environment.MachineName,
            });

        // Configure Tracing, Metrics, and Logging
        services.AddOpenTelemetry()
            .ConfigureResource(resource => resource.AddService(serviceName, serviceVersion: serviceVersion))
            .WithTracing(tracing =>
            {
                tracing
                    .SetResourceBuilder(resourceBuilder)
                    .AddAspNetCoreInstrumentation(options =>
                    {
                        // Record exception details
                        options.RecordException = true;
                        // Enrich spans with HTTP request/response data
                        options.EnrichWithHttpRequest = (activity, httpRequest) =>
                        {
                            activity.SetTag("http.request.content_length", httpRequest.ContentLength);
                            activity.SetTag("http.request.content_type", httpRequest.ContentType);
                        };
                        options.EnrichWithHttpResponse = (activity, httpResponse) =>
                        {
                            activity.SetTag("http.response.content_length", httpResponse.ContentLength);
                            activity.SetTag("http.response.content_type", httpResponse.ContentType);
                        };
                    })
                    .AddHttpClientInstrumentation(options =>
                    {
                        options.RecordException = true;
                        // Filter out health check requests
                        options.FilterHttpRequestMessage = (httpRequestMessage) =>
                        {
                            return !httpRequestMessage.RequestUri?.PathAndQuery.Contains("/health") ?? true;
                        };
                    })
                    .AddEntityFrameworkCoreInstrumentation(options =>
                    {
                        // Include sensitive data (database queries) only in development
                        options.SetDbStatementForText = environment.IsDevelopment();
                        options.SetDbStatementForStoredProcedure = environment.IsDevelopment();
                    })
                    .AddOtlpExporter(options =>
                    {
                        options.Endpoint = new Uri(otlpGrpcEndpoint);
                        options.Protocol = OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
                    });
            })
            .WithMetrics(metrics =>
            {
                metrics
                    .SetResourceBuilder(resourceBuilder)
                    // Add ASP.NET Core metrics (HTTP request metrics)
                    .AddAspNetCoreInstrumentation()
                    // Add HTTP client metrics
                    .AddHttpClientInstrumentation()
                    // Add runtime metrics (GC, thread pool, etc.)
                    .AddRuntimeInstrumentation()
                    // Add process metrics (CPU, memory, etc.)
                    .AddProcessInstrumentation()
                    .AddOtlpExporter(options =>
                    {
                        options.Endpoint = new Uri(otlpGrpcEndpoint);
                        options.Protocol = OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
                    });
            })
            .WithLogging(logging =>
            {
                logging
                    .AddOtlpExporter(options =>
                    {
                        options.Endpoint = new Uri(otlpGrpcEndpoint);
                        options.Protocol = OpenTelemetry.Exporter.OtlpExportProtocol.Grpc;
                    });
            });

        // Integrate OpenTelemetry with ASP.NET Core logging
        services.AddLogging(logging =>
        {
            logging.AddOpenTelemetry(options =>
            {
                options.IncludeScopes = true;
                options.IncludeFormattedMessage = true;
            });
        });

        return services;
    }
}
