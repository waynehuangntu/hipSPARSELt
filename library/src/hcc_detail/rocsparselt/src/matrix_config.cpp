#include "matrix_config.h"
#include <math.h>

MatrixConfig find_nearest_config(int x, int y) {
    double min_distance = INFINITY;
    int nearest_index = 0;
    
    // Find the configuration with the minimum Euclidean distance
    for (int i = 0; i < MATRIX_CONFIG_COUNT; i++) {
        double dx = matrix_configs[i].x - x;
        double dy = matrix_configs[i].y - y;
        double distance = dx*dx + dy*dy;
        
        if (distance < min_distance) {
            min_distance = distance;
            nearest_index = i;
        }
    }
    
    return matrix_configs[nearest_index];
}

MatrixConfig find_upright_config(int x, int y) {
    int min_x = INT_MAX;
    int min_y = INT_MAX;
    int nearest_index = 0;
    
    // Find the smallest configuration that is >= both x and y
    for (int i = 0; i < MATRIX_CONFIG_COUNT; i++) {
        if (matrix_configs[i].x >= x && matrix_configs[i].y >= y) {
            // Check if this config is "smaller" than our current best
            if (matrix_configs[i].x <= min_x && matrix_configs[i].y <= min_y) {
                min_x = matrix_configs[i].x;
                min_y = matrix_configs[i].y;
                nearest_index = i;
            }
        }
    }
    
    // If no valid config found (all configs are smaller), return the largest available
    if (min_x == INT_MAX) {
        int max_x = 0;
        int max_y = 0;
        for (int i = 0; i < MATRIX_CONFIG_COUNT; i++) {
            if (matrix_configs[i].x >= max_x && matrix_configs[i].y >= max_y) {
                max_x = matrix_configs[i].x;
                max_y = matrix_configs[i].y;
                nearest_index = i;
            }
        }
    }
    
    return matrix_configs[nearest_index];
}