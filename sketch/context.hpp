#ifndef CONTEXT_HPP
#define CONTEXT_HPP

#include "../utility/exception.hpp"
#include "../utility/randgen.hpp"
#include <boost/mpi.hpp>

namespace skylark { namespace sketch {

/**
 * A structure that holds basic information about the MPI world and what the
 * user wants to implement.
 */
struct context_t {
    /// Communicator to use for MPI
    boost::mpi::communicator comm;
    /// Rank of the current process
    int rank;
    /// Number of processes in the group
    int size;
private:
    /// Internal counter identifying the start of next stream of random numbers
    size_t _counter;
    /// The seed used for initializing the context
    int _seed;

public:
    /**
     * Initialize context with a seed and the communicator.
     * @param[in] seed Random seed to be used for all computations.
     * @param[in] orig Communicator that is duplicated and used with SKYLARK.
     *
     * @caveat This is a global operation since all MPI ranks need to
     * participate in the duplication of the communicator.
     */
    context_t (int seed,
               const boost::mpi::communicator& orig) :
        comm(orig, boost::mpi::comm_duplicate),
        rank(comm.rank()),
        size(comm.size()),
        _counter(0),
        _seed(seed) {}


    /**
     * Returns a container of samples drawn from a distribution
     * to be accessed as an array.
     * @param[in] size The size of the container.
     * @param[in] distribution The distribution to draw samples from.
     * @return Random samples' container.
     *
     * @details This is the main facility for creating a "stream" of
     * samples of given size and distribution. size is needed for
     * reserving up-front a portion of the linear space of the 2^64 samples
     * that can be provided by a context with a fixed seed.
     *
     * @internal We currently use Random123 library, most specifically
     * Threefry4x64 counter-based generator, as wrapped by the uniform
     * random generator, MicroURNG. For each sample we instantiate
     * a MicroURNG instance. Each such instance needs 2 arrays of 4 uint64
     * numbers each, namely a counter and a key: we successively increment only
     * the first uint64 component in counter (counter[0]) and fix key to be
     * the seed. This instance is then passed to the distribution. This
     * in turn calls operator () on the instance and increments counter[3]
     * accordingly (for multiple calls), thus ensuring the independence
     * of successive samples. operator () can either trigger a run of
     * the Threefry4x64 algorithm for creating a fresh result array
     * (also consisting of 4 uint64's) and use one or more of its components or
     * use those components from a previous run that are not processed yet. 
     *
     * @caveat This should be used as a global operation to keep the
     * the internal state of the context synchronized.
     */
    template <typename ValueType,
              typename Distribution>
    skylark::utility::random_samples_array_t<ValueType, Distribution>
    allocate_random_samples_array(size_t size, Distribution& distribution) {
        try {
          skylark::utility::random_samples_array_t<ValueType, Distribution>
              random_samples_array(_counter, size, _seed, distribution);
          _counter = _counter + size;
          return random_samples_array;
        } catch (std::runtime_error e) {
            SKYLARK_THROW_EXCEPTION (
                utility::skylark_exception()
                << utility::error_msg(e.what()) );
        }
    }


    /**
     * Returns a container of random numbers to be accessed as an array.
     * @param[in] size The size of the container.
     * @return Random numbers' container.
     *
     * @caveat This should be used as a global operation to keep the
     * the internal state of the context synchronized.
     */
    skylark::utility::random_array_t allocate_random_array(size_t size) {
        try {
            skylark::utility::random_array_t
                random_array(_counter, size, _seed);
            _counter = _counter + size;
            return random_array;
        } catch (std::runtime_error e) {
            SKYLARK_THROW_EXCEPTION (
                utility::skylark_exception()
                << utility::error_msg(e.what()) );
        }
    }


    /**
     * Returns an integer random number.
     * @return Random integer number.
     *
     * @caveat This should be used as a global operation to keep the
     * the internal state of the context synchronized.
     */
     int random_int() {
         skylark::utility::random_array_t random_array =
             allocate_random_array(1);
         int sample = random_array[0];
         return sample;
    }
};

} } /** skylark::sketch */

#endif // CONTEXT_HPP
