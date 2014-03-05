#ifndef SKYLARK_WZT_DATA_HPP
#define SKYLARK_WZT_DATA_HPP

#include "../utility/exception.hpp"
#include "../utility/distributions.hpp"

#include "transform_data.hpp"
#include "hash_transform_data.hpp"

namespace skylark { namespace sketch {

/**
 * Woodruff-Zhang Transform (data)
 *
 * Woodruff-Zhang Transform is very similar to the Clarkson-Woodruff Transform:
 * it replaces the +1/-1 diagonal with reciprocal exponential random entries.
 * It is suitable for lp regression with 1 <= p <= 2.
 *
 * Reference:
 * D. Woodruff and Q. Zhang
 * Subspace Embeddings and L_p Regression Using Exponential Random
 * COLT 2013
 *
 * TODO current implementation is only one sketch index, when for 1 <= p <= 2
 *      you want more than one.
 */
template<typename IndexType, typename ValueType>
struct WZT_data_t : public hash_transform_data_t<
    IndexType, ValueType,
    boost::random::uniform_int_distribution,
    boost::random::exponential_distribution > {

    typedef hash_transform_data_t<
        IndexType, ValueType,
        boost::random::uniform_int_distribution,
        boost::random::exponential_distribution >  Base;

    WZT_data_t(int N, int S, double p, context_t& context)
        : Base(N, S, context, "WZT"), _P(p) {

        // TODO verify that p is in the correct range.
        if(p < 1 || 2 < p)
            SKYLARK_THROW_EXCEPTION (
                utility::sketch_exception()
                    << utility::error_msg("WZT parameter p has unsupported range") );


        _populate();
    }

    WZT_data_t(const boost::property_tree::ptree &sketch,
               skylark::sketch::context_t& context)
        : Base(sketch, context),
        _P(sketch.get<double>("sketch.p")) {

        _populate();
    }

    template <typename IndexT, typename ValueT>
    friend boost::property_tree::ptree& operator<<(
            boost::property_tree::ptree &sk,
            const WZT_data_t<IndexT, ValueT> &data);

private:
    double _P;

    void _populate() {

        // Since the distribution depends on the target p we have to pass p as
        // a parameter. We also cannot just use the distribution as template.
        // The only solution I found is to let the base class generate the
        // numbers and then modify them to the correct distribution.
        // We also need it to +/- with equal probability. This solves this as
        // well.
        utility::rademacher_distribution_t<ValueType> pmdist;
        std::vector<ValueType> pmvals =
            Base::context.generate_random_samples_array(Base::N, pmdist);
        for(int i = 0; i < Base::N; i++)
             Base::row_value[i] =
                 pmvals[i] * pow(1.0 / Base::row_value[i], 1.0 / _P);

    }
};

template <typename IndexType, typename ValueType>
boost::property_tree::ptree& operator<<(
        boost::property_tree::ptree &sk,
        const WZT_data_t<IndexType, ValueType> &data) {

    sk << static_cast<const transform_data_t&>(data);
    sk.put("sketch.p", data._P);
    return sk;
}

} } /** namespace skylark::sketch */

#endif // SKYLARK_MMT_DATA_HPP
