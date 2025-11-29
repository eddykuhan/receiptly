using Microsoft.EntityFrameworkCore;
using Receiptly.Infrastructure.Data;
using Serilog;

namespace Receiptly.API.Configuration;

public static class WebApplicationExtensions
{
    public static async Task<WebApplication> ApplyDatabaseMigrations(this WebApplication app)
    {
        if (app.Environment.IsDevelopment())
        {
            using var scope = app.Services.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            try
            {
                Log.Information("Applying database migrations...");
                await dbContext.Database.MigrateAsync();
                Log.Information("Database migrations applied successfully");
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Could not apply database migrations. Database may not be available yet.");
            }
        }

        return app;
    }

    public static WebApplication ConfigureMiddleware(this WebApplication app)
    {
        // Configure Swagger (non-production or explicitly enabled)
        if (!app.Environment.IsProduction() || app.Configuration.GetValue<bool>("Swagger:Enabled", false))
        {
            app.UseSwagger();
            app.UseSwaggerUI();
        }

        // HTTPS redirection disabled - enable in production with proper certificates
        // app.UseHttpsRedirection();

        // CORS
           app.UseCors("AllowAngularApp");
        // if (app.Environment.IsDevelopment())
        // {
        //     app.UseCors("AllowAngularApp");
        // }
        // else
        // {
        //     app.UseCors("Production");
        // }

        // Request logging
        app.UseSerilogRequestLogging();

        return app;
    }

    public static WebApplication MapEndpoints(this WebApplication app)
    {
        // Health check endpoint
        app.MapGet("/health", () => Results.Ok(new
        {
            status = "healthy",
            service = "receiptly-api",
            timestamp = DateTime.UtcNow
        }));

        // Controllers
        app.MapControllers();

        return app;
    }
}
