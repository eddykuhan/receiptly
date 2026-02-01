using Microsoft.EntityFrameworkCore;
using Receiptly.API.Middleware;
using Receiptly.Infrastructure.Data;

namespace Receiptly.API.Configuration;

public static class WebApplicationExtensions
{
    public static async Task<WebApplication> ApplyDatabaseMigrations(this WebApplication app)
    {
        if (app.Environment.IsDevelopment())
        {
            using var scope = app.Services.CreateScope();
            var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            var logger = scope.ServiceProvider.GetRequiredService<ILogger<ApplicationDbContext>>();
            try
            {
                logger.LogInformation("Applying database migrations...");
                await dbContext.Database.MigrateAsync();
                logger.LogInformation("Database migrations applied successfully");
            }
            catch (Exception ex)
            {
                logger.LogWarning(ex, "Could not apply database migrations. Database may not be available yet.");
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

        // Clerk JWT authentication middleware
        app.UseMiddleware<ClerkJwtMiddleware>();

        // Request logging (using ASP.NET Core built-in logging)
        app.UseHttpLogging();

        return app;
    }

    public static WebApplication MapEndpoints(this WebApplication app)
    {
        // Health check endpoint (public - no authentication required)
        app.MapGet("/health", () => Results.Ok(new
        {
            status = "healthy",
            service = "receiptly-api",
            timestamp = DateTime.UtcNow
        }))
        .AllowAnonymous(); // Allow health checks without authentication

        // Controllers
        app.MapControllers();

        return app;
    }
}
