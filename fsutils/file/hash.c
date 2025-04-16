#include <openssl/evp.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <dirent.h>
#include <sys/stat.h>
#include <string.h>
#include <threads.h>

typedef struct {
    uint8_t hash[32];  // SHA-256 hash size
} sha256_hash_t;

struct ThreadArgs {
    int startIndex;
    int endIndex;
    char **filePaths;
    sha256_hash_t **hashes;
};

/**
 * Return an array of file paths recursively along with the count.
 * @param basePath The base path from which to start listing files.
 * @param count Pointer to receive the number of files.
 * @return An array of file paths, or NULL on failure.
 */
char** listFilesRecursively(const char *basePath, int *count) {
    struct dirent *dp;
    DIR *dir = opendir(basePath);

    if (!dir) {
        printf("Error opening directory %s\n", basePath);
        return NULL;
    }

    char **result = NULL;
    int files_in_dir = 0;
    int _count = 0;
    const int initialSize = 9000000;
    result = (char **)malloc(initialSize * sizeof(char *));
    if (!result) {
        printf("Memory allocation failed\n");
        closedir(dir);
        return NULL;
    }

    char path[1024]; // Buffer to hold the full path of each entry
    while ((dp = readdir(dir)) != NULL) {
        if (strcmp(dp->d_name, ".") == 0 || strcmp(dp->d_name, "..") == 0)
            continue;

        snprintf(path, sizeof(path), "%s/%s", basePath, dp->d_name);

        if (dp->d_type == DT_DIR) {
            char **subResult = listFilesRecursively(path, count);
            if (!subResult) {
                printf("Error traversing subdirectory %s\n", path);
                continue;
            }
            for (int i = 0; subResult[i] != NULL; i++) {
                // *count = *count + 1;
                result[files_in_dir++] = subResult[i];
            }
            free(subResult);
        } else {
            // *count = *count + 1;
            result[files_in_dir++] = strdup(path);
        }
    }

    closedir(dir);
    *count = files_in_dir;
    return result;
}


sha256_hash_t * returnHash(const char *filePath) {
    sha256_hash_t *hash = (sha256_hash_t *)malloc(sizeof(sha256_hash_t));
    FILE *file = fopen(filePath, "rb");
    if (!file) {
        // printf("Error opening file %s\n", filePath);
        return NULL;
    }
    EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
    const EVP_MD *md = EVP_sha256();
    unsigned char buffer[32768]; // Larger buffer size for efficiency
    size_t bytesRead;

    if (!EVP_DigestInit_ex(mdctx, md, NULL)) {
        printf("Error initializing digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return NULL;
    }

    bytesRead = fread(buffer, 1, sizeof(buffer), file);
    if (!EVP_DigestUpdate(mdctx, buffer, bytesRead)) {
        printf("Error updating digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return NULL;
    }

    unsigned int len = sizeof(hash->hash);
    if (!EVP_DigestFinal_ex(mdctx, hash->hash, &len)) {
        printf("Error finalizing digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return NULL;
    }

    EVP_MD_CTX_free(mdctx);
    fclose(file);
    return hash;
}


/**
 * Hash a file using SHA-256.
 * @param filePath The path of the file to hash.
 * @param hash The pre-allocated buffer to store the hash.
 * @return 0 on success, -1 on failure.
 */
int hashFile(const char *filePath, sha256_hash_t *hash) {
    FILE *file = fopen(filePath, "rb");
    if (!file) {
        // printf("Error opening file %s\n", filePath);
        return -1;
    }

    EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
    const EVP_MD *md = EVP_sha256();
    unsigned char buffer[32768]; // Larger buffer size for efficiency
    size_t bytesRead;

    if (!EVP_DigestInit_ex(mdctx, md, NULL)) {
        printf("Error initializing digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return -1;
    }

    bytesRead = fread(buffer, 1, sizeof(buffer), file);
    if (!EVP_DigestUpdate(mdctx, buffer, bytesRead)) {
        printf("Error updating digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return -1;
    }

    unsigned int len = sizeof(hash->hash);
    if (!EVP_DigestFinal_ex(mdctx, hash->hash, &len)) {
        printf("Error finalizing digest\n");
        EVP_MD_CTX_free(mdctx);
        fclose(file);
        return -1;
    }

    EVP_MD_CTX_free(mdctx);
    fclose(file);
    return 0;
}

/**
 * Thread function to process a range of files.
 */
int processFiles(void *arg) {
    struct ThreadArgs *args = (struct ThreadArgs *) arg;
    for (int i = args->startIndex; i < args->endIndex; i++) {
        const char *filePath = args->filePaths[i];
        if (hashFile(filePath, args->hashes[i]) != 0) {
            args->hashes[i] = NULL;
            printf("Error hashing file %s\n", filePath);

        }
    }
    return 0;
}


/**
 Struct to represent key, value pairs where key=filepath, value=hash
 */

struct HashMapEntry {
    char *filepath; // file path
    sha256_hash_t *sha;
};
struct HashMap {
    struct HashMapEntry *entries; // array of entries
    int size; // number of entries
};
/**
  Library function to return a mapping where keys are filepaths and values are their SHA-256 hashes.
  @param directory The base directory to scan recursively.
  @return A mapping of file paths to their SHA-256 hashes, or NULL on error.
 */

struct HashMap *hashDirectory(const char *directory) {

    int numFiles = 0;
    char **filePaths = listFilesRecursively(directory, &numFiles);
    if (!filePaths) {
        return NULL;
    }
    // Allocate hashes array
    sha256_hash_t **hashes = malloc(numFiles * sizeof(sha256_hash_t *));
    for (int i = 0; filePaths[i] != NULL; i++) {
        char* path = filePaths[i];
        hashes[i] = malloc(sizeof(sha256_hash_t));
        if (!hashes[i]) {
            printf("Error allocating memory for hash\n");
            for (int j = 0; j < i; j++) {
                free(hashes[j]);
            }
            free(hashes);
            free(filePaths);
            return NULL;
        }
    }

    // Create threads
    const int numThreads = 16;
    struct ThreadArgs args[numThreads];
    thrd_t threads[numThreads];

    // Allocate memory for hash map
    struct HashMap *map = malloc(numFiles * sizeof(struct HashMapEntry) + sizeof(int) * numFiles);
    map->entries = malloc(numFiles * sizeof(struct HashMapEntry));
    map->size = numFiles;

    // Calculate the range for each thread
    for (int t = 0; t < numThreads; t++) {
        args[t].startIndex = (t * numFiles) / numThreads;
        args[t].endIndex = ((t + 1) * numFiles) / numThreads;
        if (t == numThreads - 1) {
            args[t].endIndex = numFiles;
        }
        args[t].filePaths = filePaths;
        args[t].hashes = hashes;

        int ret = thrd_create(&threads[t], processFiles, &args[t]);
        if (ret != thrd_success) {
            printf("Error creating thread %d\n", t);
            // Clean up resources
            for (int j = 0; j < numFiles; j++) {
                if (hashes[j]) free(hashes[j]);
            }
            free(hashes);
            free(filePaths);
            return NULL;
        }
    }

    // Wait for all threads to finish
    for (int t = 0; t < numThreads; t++) {
        thrd_join(threads[t], NULL);
    }

    // Return results
    for (int i = 0; i < numFiles; i++) {
        if (!hashes[i]) continue;
        map->entries[i].filepath = filePaths[i];
        map->entries[i].sha = hashes[i];//->hash;

    }

    return map;
}


int main(int argc, char* argv[]) {
    const char* dir = "/home/joona/Downloads";
    struct HashMap *result = hashDirectory(dir);
    // if (argc < 2) {
    //     printf("Usage: %s <directory>\n", argv[0]);
    //     return 1;
    // }
    // int numFiles = 0;
    // char **filePaths = listFilesRecursively(argv[1], &numFiles);
    // if (!filePaths) {
    //     return 1;
    // }
    // printf("Number of files: %d\n", numFiles);
    // // Allocate hashes array
    // sha256_hash_t **hashes = malloc(numFiles * sizeof(sha256_hash_t *));
    // if (!hashes) {
    //     printf("Error allocating memory for hashes\n");
    //     free(filePaths);
    //     return 1;
    // }

    // // Pre-allocate each hash
    // for (int i = 0; filePaths[i] != NULL; i++) {
    //     char* path = filePaths[i];
    //     hashes[i] = malloc(sizeof(sha256_hash_t));
    //     if (!hashes[i]) {
    //         printf("Error allocating memory for hash\n");
    //         for (int j = 0; j < i; j++) {
    //             free(hashes[j]);
    //         }
    //         free(hashes);
    //         free(filePaths);
    //         return 1;
    //     }
    // }

    // const int numThreads = 16;
    // struct ThreadArgs args[numThreads];
    // thrd_t threads[numThreads];

    // // Calculate the range for each thread
    // for (int t = 0; t < numThreads; t++) {
    //     args[t].startIndex = (t * numFiles) / numThreads;
    //     args[t].endIndex = ((t + 1) * numFiles) / numThreads;
    //     if (t == numThreads - 1) {
    //         args[t].endIndex = numFiles;
    //     }
    //     args[t].filePaths = filePaths;
    //     args[t].hashes = hashes;

    //     int ret = thrd_create(&threads[t], processFiles, &args[t]);
    //     if (ret != thrd_success) {
    //         printf("Error creating thread %d\n", t);
    //         // Clean up resources
    //         for (int j = 0; j < numFiles; j++) {
    //             if (hashes[j]) free(hashes[j]);
    //         }
    //         free(hashes);
    //         free(filePaths);
    //         return 1;
    //     }
    // }

    // // Wait for all threads to finish
    // for (int t = 0; t < numThreads; t++) {
    //     thrd_join(threads[t], NULL);
    // }

    // // Print the results
    // for (int i = 0; i < numFiles; i++) {
    //     if (!hashes[i]) continue;
    //     printf("%-80s: ", filePaths[i]);
    //     for (int j = 0; j < 32; j++) {
    //         printf("%02x", hashes[i]->hash[j]);
    //     }
    //     printf("\n");
    // }

    // // Free resources
    // for (int i = 0; i < numFiles; i++) {
    //     free(hashes[i]);
    // }
    // free(hashes);
    // for (int i = 0; i < numFiles; i++) {
    //     free(filePaths[i]);
    // }
    // free(filePaths);

    // return 0;
}
